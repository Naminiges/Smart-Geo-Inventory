from geoalchemy2 import Geometry
from datetime import datetime
from app import db
from app.models.base import BaseModel


class Distribution(BaseModel):
    """Distribution model for field installations and general distribution"""
    __tablename__ = 'distributions'

    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), unique=True, nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    field_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Made nullable for draft status
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=True)
    address = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS geometry for GIS
    installed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default='installing')  # draft, installing, in_transit, installed, broken, maintenance
    note = db.Column(db.Text)

    # Link to asset request (if created from asset request)
    asset_request_id = db.Column(db.Integer, db.ForeignKey('asset_requests.id'), nullable=True)
    asset_request_item_id = db.Column(db.Integer, db.ForeignKey('asset_request_items.id'), nullable=True)

    # Draft verification fields (for general distribution by warehouse staff)
    is_draft = db.Column(db.Boolean, default=False)  # True if this is a draft distribution awaiting admin verification
    draft_created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Warehouse staff who created the draft
    draft_notes = db.Column(db.Text)  # Notes from warehouse staff when creating draft
    draft_verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who verified the draft
    draft_verified_at = db.Column(db.DateTime)  # When draft was verified
    draft_rejected = db.Column(db.Boolean, default=False)  # True if draft was rejected
    draft_rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who rejected the draft
    draft_rejected_at = db.Column(db.DateTime)  # When draft was rejected
    draft_rejection_reason = db.Column(db.Text)  # Reason if draft was rejected

    # Task type and verification fields
    task_type = db.Column(db.String(50), default='installation')  # installation, delivery
    verification_photo = db.Column(db.LargeBinary)  # BLOB to store verification photo as bytes
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
    draft_creator = db.relationship('User', foreign_keys=[draft_created_by], backref='draft_distributions_created')
    draft_verifier = db.relationship('User', foreign_keys=[draft_verified_by], backref='draft_distributions_verified')
    draft_rejector = db.relationship('User', foreign_keys=[draft_rejected_by], backref='draft_distributions_rejected')
    unit = db.relationship('Unit', back_populates='distributions')
    unit_detail = db.relationship('UnitDetail', back_populates='distributions')
    asset_request = db.relationship('AssetRequest', foreign_keys=[asset_request_id], backref='distributions')
    asset_request_item = db.relationship('AssetRequestItem', foreign_keys=[asset_request_item_id], backref='distributions')

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

    def submit_verification(self, photo_bytes=None, notes=None):
        """Submit verification by field staff"""
        if self.verification_status == 'verified':
            return False, 'Tugas ini sudah diverifikasi'
        self.verification_status = 'submitted'
        self.verification_photo = photo_bytes  # Store photo as BLOB
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

    def verify_draft(self, user_id, notes=None):
        """Verify draft distribution by admin - converts draft to active distribution"""
        if not self.is_draft:
            return False, 'Ini bukan draft distribusi'

        self.is_draft = False
        self.draft_verified_by = user_id
        self.draft_verified_at = datetime.utcnow()
        if notes:
            self.draft_notes = notes

        # Set field_staff to admin if not assigned
        if not self.field_staff_id:
            self.field_staff_id = user_id

        # Determine initial status based on task type
        category_name = self.item_detail.item.category.name.lower() if self.item_detail and self.item_detail.item and self.item_detail.item.category else ''
        self.task_type = 'installation' if 'jaringan' in category_name or 'network' in category_name else 'delivery'
        self.status = 'installing' if self.task_type == 'installation' else 'in_transit'

        # Update item detail status to processing
        if self.item_detail:
            self.item_detail.status = 'processing'
            self.item_detail.save()

        self.save()
        return True, 'Draft distribusi berhasil diverifikasi'

    def reject_draft(self, user_id, reason=None):
        """Reject draft distribution by admin"""
        if not self.is_draft:
            return False, 'Ini bukan draft distribusi'

        self.is_draft = False  # Mark as not draft anymore
        self.draft_rejected = True
        self.draft_rejected_by = user_id
        self.draft_rejected_at = datetime.utcnow()
        self.draft_rejection_reason = reason
        self.status = 'rejected'
        self.save()

        # Return item detail status to available
        if self.item_detail:
            self.item_detail.status = 'available'
            self.item_detail.save()

        return True, 'Draft distribusi berhasil ditolak'

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

    @property
    def is_networking_item(self):
        """Check if this distribution is for networking equipment"""
        if self.item_detail and self.item_detail.item and self.item_detail.item.category:
            category_name = self.item_detail.item.category.name.lower()
            # Check for networking-related categories
            networking_keywords = ['networking', 'jaringan', 'network', 'router', 'switch', 'wifi', 'wireless', 'access point', 'ap']
            return any(keyword in category_name for keyword in networking_keywords)
        return False

    @property
    def requires_installation(self):
        """Check if this distribution requires installation (networking) or just delivery"""
        return self.is_networking_item

    @staticmethod
    def create_from_asset_request_item(asset_request_item, warehouse_id, field_staff_id, item_detail_id):
        """
        Create distribution from asset request item

        Args:
            asset_request_item: AssetRequestItem object
            warehouse_id: Source warehouse ID
            field_staff_id: Assigned field staff ID
            item_detail_id: ItemDetail ID with serial number to distribute

        Returns:
            Distribution object
        """
        from app.models.asset_request import AssetRequest
        from app.models.distribution import Distribution

        asset_request = asset_request_item.asset_request

        # Determine task type based on item category
        task_type = 'installation' if asset_request_item.item.category.name.lower() in ['networking', 'jaringan'] else 'delivery'

        # Create distribution
        distribution = Distribution(
            item_detail_id=item_detail_id,
            warehouse_id=warehouse_id,
            field_staff_id=field_staff_id,
            unit_id=asset_request.unit_id,
            unit_detail_id=asset_request_item.unit_detail_id if asset_request_item.unit_detail_id else asset_request.unit.unit_details[0].id if asset_request.unit and asset_request.unit.unit_details else None,
            address=asset_request.unit.address if asset_request.unit else 'Unknown',
            task_type=task_type,
            asset_request_id=asset_request.id,
            asset_request_item_id=asset_request_item.id,
            status='installing' if task_type == 'installation' else 'in_transit'
        )

        # Set coordinates from unit if available
        if asset_request.unit and asset_request.unit.geom:
            distribution.geom = asset_request.unit.geom

        distribution.save()

        # Update item detail status
        if item_detail_id:
            from app.models.master_data import ItemDetail
            item_detail = ItemDetail.query.get(item_detail_id)
            if item_detail:
                item_detail.status = 'processing'
                item_detail.save()

        # Update asset request item status
        asset_request_item.status = 'distributing'
        asset_request_item.save()

        return distribution

    @staticmethod
    def bulk_create_from_asset_request(asset_request, distribution_data):
        """
        Bulk create distributions from asset request

        Args:
            asset_request: AssetRequest object
            distribution_data: List of dicts with keys:
                - asset_request_item_id
                - warehouse_id
                - field_staff_id
                - item_detail_id

        Returns:
            List of created Distribution objects
        """
        distributions = []

        for data in distribution_data:
            from app.models.asset_request import AssetRequestItem

            asset_request_item = AssetRequestItem.query.get(data['asset_request_item_id'])
            if not asset_request_item:
                continue

            distribution = Distribution.create_from_asset_request_item(
                asset_request_item=asset_request_item,
                warehouse_id=data['warehouse_id'],
                field_staff_id=data['field_staff_id'],
                item_detail_id=data['item_detail_id']
            )

            distributions.append(distribution)

        # Update asset request status and link distribution
        if distributions:
            asset_request.distribution_id = distributions[0].id  # Link first distribution
            asset_request.status = 'distributing'
            asset_request.save()

        return distributions
