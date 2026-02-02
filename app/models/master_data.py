from geoalchemy2 import Geometry
from app import db
from app.models.base import BaseModel


class Category(BaseModel):
    """Category model for item classification"""
    __tablename__ = 'categories'

    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), nullable=False, unique=True)  # Category code for item_code prefix (e.g., JAR, ELE, SRV)
    description = db.Column(db.Text)
    require_serial_number = db.Column(db.Boolean, default=False, nullable=False)  # Wajib serial number atau tidak

    # Relationships
    items = db.relationship('Item', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name} ({self.code})>'


class Item(BaseModel):
    """Item model for product catalog"""
    __tablename__ = 'items'

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    item_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(50), nullable=False)  # e.g., pcs, box, unit

    # Relationships
    category = db.relationship('Category', back_populates='items')
    item_details = db.relationship('ItemDetail', back_populates='item', lazy='dynamic')
    stocks = db.relationship('Stock', back_populates='item', lazy='dynamic')

    @property
    def total_stock(self):
        """Get total stock across all warehouses"""
        from app.models.inventory import Stock
        result = db.session.query(db.func.sum(Stock.quantity)).filter(Stock.item_id == self.id).scalar()
        return result or 0

    @property
    def total_details(self):
        """Get total item details (serial numbers) count"""
        return self.item_details.count()

    @property
    def available_details(self):
        """Get total available item details count"""
        return self.item_details.filter_by(status='available').count()

    @property
    def used_details(self):
        """Get total used item details count"""
        return self.item_details.filter_by(status='used').count()

    @property
    def in_unit_details(self):
        """Get total item details in unit count"""
        return self.item_details.filter_by(status='in_unit').count()

    @property
    def processing_details(self):
        """Get total processing item details count"""
        return self.item_details.filter_by(status='processing').count()

    @property
    def maintenance_details(self):
        """Get total maintenance item details count"""
        return self.item_details.filter_by(status='maintenance').count()

    @property
    def returned_details(self):
        """Get total returned item details count (includes maintenance status)"""
        return self.item_details.filter(db.or_(
            ItemDetail.status == 'returned',
            ItemDetail.status == 'maintenance'
        )).count()

    def get_total_stock(self, warehouse_id=None):
        """Get total stock across all warehouses or specific warehouse"""
        from app.models.inventory import Stock
        query = db.session.query(db.func.sum(Stock.quantity)).filter(Stock.item_id == self.id)
        if warehouse_id:
            query = query.filter(Stock.warehouse_id == warehouse_id)
        return query.scalar() or 0

    def __repr__(self):
        return f'<Item {self.item_code} - {self.name}>'


class ItemDetail(BaseModel):
    """Item detail model for individual units with serial numbers"""
    __tablename__ = 'item_details'

    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    serial_unit = db.Column(db.String(100))  # Serial unit internal untuk tracking aset
    status = db.Column(db.String(50), default='available')  # available, processing, maintenance, used, in_unit, returned
    specification_notes = db.Column(db.Text)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))

    # Relationships
    item = db.relationship('Item', back_populates='item_details')
    warehouse = db.relationship('Warehouse', back_populates='item_details')
    distribution = db.relationship('Distribution', uselist=False, back_populates='item_detail')

    @property
    def unit_name(self):
        """Get unit name from distribution if status is in_unit or used"""
        if self.status in ['in_unit', 'used'] and self.distribution and self.distribution.unit:
            return self.distribution.unit.name
        return None

    def __repr__(self):
        return f'<ItemDetail {self.serial_number}>'


class Warehouse(BaseModel):
    """Warehouse model with GIS support"""
    __tablename__ = 'warehouses'

    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry('POINT', srid=4326))  # PostGIS geometry for GIS

    # Relationships
    item_details = db.relationship('ItemDetail', back_populates='warehouse', lazy='dynamic')
    stocks = db.relationship('Stock', back_populates='warehouse', lazy='dynamic')
    users = db.relationship('User', back_populates='warehouse', lazy='dynamic')
    distributions = db.relationship('Distribution', back_populates='warehouse', lazy='dynamic')

    def set_coordinates(self, latitude, longitude):
        """Set point geometry from latitude and longitude"""
        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
        self.geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    def get_coordinates(self):
        """Get latitude and longitude from geometry"""
        if self.geom:
            from geoalchemy2.functions import ST_X, ST_Y
            # Convert WKT to coordinates
            wkt = db.session.execute(
                db.select(ST_X(self.geom), ST_Y(self.geom))
            ).first()
            if wkt:
                return {'latitude': float(wkt[1]), 'longitude': float(wkt[0])}
        return None

    def __repr__(self):
        return f'<Warehouse {self.name}>'
