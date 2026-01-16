from datetime import datetime
from app import db
from app.models.base import BaseModel


class Stock(BaseModel):
    """Stock model for inventory tracking per warehouse"""
    __tablename__ = 'stocks'

    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    item = db.relationship('Item', back_populates='stocks')
    warehouse = db.relationship('Warehouse', back_populates='stocks')

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('item_id', 'warehouse_id', name='unique_item_warehouse'),
    )

    def add_stock(self, quantity):
        """Add stock quantity"""
        self.quantity += quantity
        self.updated_at = datetime.utcnow()
        self.save()

    def remove_stock(self, quantity):
        """Remove stock quantity"""
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.updated_at = datetime.utcnow()
            self.save()
            return True
        return False

    def is_low_stock(self, threshold=10):
        """Check if stock is below threshold"""
        return self.quantity < threshold

    def __repr__(self):
        return f'<Stock Item:{self.item_id} Warehouse:{self.warehouse_id} Qty:{self.quantity}>'


class StockTransaction(BaseModel):
    """Stock transaction log for tracking movements"""
    __tablename__ = 'stock_transactions'

    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # IN | OUT
    quantity = db.Column(db.Integer, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    note = db.Column(db.Text)

    # Relationships
    item = db.relationship('Item')
    warehouse = db.relationship('Warehouse')

    def __repr__(self):
        return f'<StockTransaction {self.transaction_type} {self.quantity}>'
