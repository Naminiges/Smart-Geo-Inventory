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
    status = db.Column(db.String(50), default='installing')  # installing, installed, broken, maintenance
    note = db.Column(db.Text)

    # Relationships
    item_detail = db.relationship('ItemDetail', back_populates='distribution')
    warehouse = db.relationship('Warehouse', back_populates='distributions')
    field_staff = db.relationship('User', foreign_keys=[field_staff_id], back_populates='distributions')
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

    def __repr__(self):
        return f'<Distribution Item:{self.item_detail_id} Status:{self.status}>'
