from geoalchemy2 import Geometry
from datetime import datetime
from app import db
from app.models.base import BaseModel


class Distribution(BaseModel):
    """Distribution model for field installations"""
    __tablename__ = 'distributions'

    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), unique=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    field_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=False)
    address = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS geometry for GIS
    installed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default='installing')  # installing, in_transit, installed, broken, maintenance
    note = db.Column(db.Text)

    # Task type and verification fields
    task_type = db.Column(db.String(50), default='installation')  # installation, delivery
    verification_photo = db.Column(db.String(500))  # Path to uploaded verification photo
    verification_notes = db.Column(db.Text)  # Notes from field staff
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Warehouse staff who verified
    verified_at = db.Column(db.DateTime)  # When warehouse staff verified
    verification_status = db.Column(db.String(50), default='pending')  # pending, submitted, verified, rejected
    verification_rejection_reason = db.Column(db.Text)  # Reason if rejected

    # Relationships
    item_detail = db.relationship('ItemDetail', back_populates='distribution')
    warehouse = db.relationship('Warehouse', back_populates='distributions')
    field_staff = db.relationship('User', foreign_keys=[field_staff_id], back_populates='distributions')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_distributions')
    unit = db.relationship('Unit', back_populates='distributions')
    unit_detail = db.relationship('UnitDetail', back_populates='distributions')

    def set_coordinates(self, latitude, longitude):
        """Set point geometry from latitude and longitude"""
        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
        self.geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    def get_coordinates(self):
        """Get latitude and longitude from geometry"""
        if self.geom:
            from geoalchemy2.functions import ST_X, ST_Y
            wkt = db.session.execute(
                db.select(ST_X(self.geom), ST_Y(self.geom))
            ).first()
            if wkt:
                return {'latitude': float(wkt[1]), 'longitude': float(wkt[0])}
        return None

    def mark_installed(self):
        """Mark distribution as installed"""
        self.status = 'installed'
        self.save()

    def mark_broken(self):
        """Mark distribution as broken"""
        self.status = 'broken'
        self.save()

    def mark_maintenance(self):
        """Mark distribution as under maintenance"""
        self.status = 'maintenance'
        self.save()

    def submit_verification(self, photo_path=None, notes=None):
        """Submit verification by field staff"""
        if self.verification_status == 'verified':
            return False, 'Tugas ini sudah diverifikasi'
        self.verification_status = 'submitted'
        self.verification_photo = photo_path
        self.verification_notes = notes
        self.save()
        return True, 'Verifikasi berhasil dikirim'

    def verify_task(self, user_id):
        """Verify task completion by warehouse staff"""
        if self.verification_status != 'submitted':
            return False, 'Tugas belum dikirim untuk verifikasi'
        self.verification_status = 'verified'
        self.verified_by = user_id
        self.verified_at = datetime.utcnow()
        self.status = 'installed'
        self.save()

        # Update item detail status
        if self.item_detail:
            self.item_detail.status = 'used'
            self.item_detail.save()
        return True, 'Tugas berhasil diverifikasi'

    def reject_verification(self, user_id, reason=None):
        """Reject verification by warehouse staff"""
        if self.verification_status != 'submitted':
            return False, 'Tugas belum dikirim untuk verifikasi'
        self.verification_status = 'rejected'
        self.verified_by = user_id
        self.verified_at = datetime.utcnow()
        self.verification_rejection_reason = reason
        self.save()
        return True, 'Verifikasi ditolak'

    def mark_in_transit(self):
        """Mark distribution as in transit (for delivery tasks)"""
        self.status = 'in_transit'
        self.save()

    @property
    def task_description(self):
        """Get task description based on task type"""
        if self.task_type == 'installation':
            return f"Instalasi {self.item_detail.item.name if self.item_detail and self.item_detail.item else 'Item'}"
        elif self.task_type == 'delivery':
            return f"Pengiriman {self.item_detail.item.name if self.item_detail and self.item_detail.item else 'Item'}"
        return "Tugas"

    @property
    def status_display(self):
        """Get display status"""
        status_map = {
            'installing': 'Sedang Dipasang',
            'in_transit': 'Sedang Dikirim',
            'installed': 'Terpasang',
            'broken': 'Rusak',
            'maintenance': 'Maintenance'
        }
        return status_map.get(self.status, self.status)

    @property
    def verification_status_display(self):
        """Get verification status display"""
        status_map = {
            'pending': 'Belum Dikerjakan',
            'submitted': 'Menunggu Verifikasi',
            'verified': 'Terverifikasi',
            'rejected': 'Ditolak'
        }
        return status_map.get(self.verification_status, self.verification_status)

    def __repr__(self):
        return f'<Distribution Item:{self.item_detail_id} Status:{self.status}>'
