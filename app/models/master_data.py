from geoalchemy2 import Geometry
from app import db
from app.models.base import BaseModel


class Category(BaseModel):
    """Category model for item classification"""
    __tablename__ = 'categories'

    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)

    # Relationships
    items = db.relationship('Item', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


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

    def get_total_stock(self, warehouse_id=None):
        """Get total stock across all warehouses or specific warehouse"""
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
    status = db.Column(db.String(50), default='available')  # available, processing, maintenance, used
    specification_notes = db.Column(db.Text)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))

    # Relationships
    item = db.relationship('Item', back_populates='item_details')
    supplier = db.relationship('Supplier', back_populates='item_details')
    warehouse = db.relationship('Warehouse', back_populates='item_details')
    distribution = db.relationship('Distribution', uselist=False, back_populates='item_detail')

    def __repr__(self):
        return f'<ItemDetail {self.serial_number}>'


class Supplier(BaseModel):
    """Supplier model for vendor management"""
    __tablename__ = 'suppliers'

    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)

    # Relationships
    item_details = db.relationship('ItemDetail', back_populates='supplier', lazy='dynamic')

    def __repr__(self):
        return f'<Supplier {self.name}>'


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
