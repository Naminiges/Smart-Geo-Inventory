from geoalchemy2 import Geometry
from app import db
from app.models.base import BaseModel


class Building(BaseModel):
    """Building model for gedung/structures"""
    __tablename__ = 'buildings'

    code = db.Column(db.String(50), unique=True, nullable=False, comment='Kode Gedung (contoh: GD.A, GD.B)')
    name = db.Column(db.String(200), nullable=False, comment='Nama Gedung')
    address = db.Column(db.Text, comment='Alamat lengkap')
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS point untuk marker
    zone_geom = db.Column(Geometry('POLYGON', srid=4326))  # PostGIS polygon untuk zona
    zone_json = db.Column(db.Text)  # GeoJSON zona
    floor_count = db.Column(db.Integer, default=1, comment='Jumlah lantai')

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
        return f'<Building {self.code} - {self.name}>'


class Unit(BaseModel):
    """Unit model for departments/sections (tenants)"""
    __tablename__ = 'units'

    name = db.Column(db.String(200), nullable=False, comment='Nama Unit/Departemen')
    address = db.Column(db.Text)
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS geometry untuk marker point
    zone_geom = db.Column(Geometry('POLYGON', srid=4326))  # PostGIS geometry untuk zona polygon
    zone_json = db.Column(db.Text)  # Store complete zone GeoJSON as text
    status = db.Column(db.String(50), default='available')  # available, in_use, maintenance

    # Relationships
    distributions = db.relationship('Distribution', back_populates='unit', lazy='dynamic')

    @property
    def items_count(self):
        """Get count of items installed in this unit (from distributions)"""
        return self.distributions.filter_by(status='installed').count()

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
    """Unit detail model for rooms/specific points within buildings"""
    __tablename__ = 'unit_details'

    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_name = db.Column(db.String(200), comment='Nama Ruangan/Titik Spesifik')
    floor = db.Column(db.String(50))
    description = db.Column(db.Text)

    # Relationships
    building = db.relationship('Building', lazy='joined')
    distributions = db.relationship('Distribution', back_populates='unit_detail', lazy='dynamic')

    def __repr__(self):
        return f'<UnitDetail {self.room_name}>'
