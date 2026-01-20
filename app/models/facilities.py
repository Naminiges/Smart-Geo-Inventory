from geoalchemy2 import Geometry
from app import db
from app.models.base import BaseModel


class Unit(BaseModel):
    """Unit model for buildings/sites"""
    __tablename__ = 'units'

    name = db.Column(db.String(200), nullable=False, comment='Nama Gedung/Site')
    address = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS geometry for GIS
    status = db.Column(db.String(50), default='available')  # available, in_use, maintenance

    # Relationships
    unit_details = db.relationship('UnitDetail', back_populates='unit', lazy='dynamic')
    distributions = db.relationship('Distribution', back_populates='unit', lazy='dynamic')

    @property
    def items_count(self):
        """Get count of unit details (items) in this unit"""
        return self.unit_details.count()

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

    def __repr__(self):
        return f'<Unit {self.name}>'


class UnitDetail(BaseModel):
    """Unit detail model for rooms/specific points within units"""
    __tablename__ = 'unit_details'

    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    room_name = db.Column(db.String(200), comment='Nama Ruangan/Titik Spesifik')
    floor = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Relationships
    unit = db.relationship('Unit', back_populates='unit_details')
    distributions = db.relationship('Distribution', back_populates='unit_detail', lazy='dynamic')

    def __repr__(self):
        return f'<UnitDetail {self.room_name}>'
