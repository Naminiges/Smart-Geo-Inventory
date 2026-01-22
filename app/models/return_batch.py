from datetime import datetime
from app import db
from app.models.base import BaseModel


class ReturnBatch(BaseModel):
    """ReturnBatch model for grouping returned items from units"""
    __tablename__ = 'return_batches'

    batch_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    return_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, cancelled

    # Tracking fields
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    confirmed_at = db.Column(db.DateTime)

    # Relationships
    warehouse = db.relationship('Warehouse', backref='return_batches')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_return_batches')
    confirmer = db.relationship('User', foreign_keys=[confirmed_by], backref='confirmed_return_batches')
    return_items = db.relationship('ReturnItem', back_populates='return_batch', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ReturnBatch {self.batch_code} - {self.status}>'

    @property
    def status_display(self):
        """Get display status"""
        status_map = {
            'pending': 'Pending',
            'confirmed': 'Dikonfirmasi',
            'cancelled': 'Dibatalkan'
        }
        return status_map.get(self.status, self.status)

    def confirm(self, user_id):
        """Confirm the return batch and update item statuses"""
        if self.status != 'pending':
            return False, 'Hanya batch dengan status pending yang dapat dikonfirmasi'

        from app.models.master_data import ItemDetail

        # Update all return items
        for item in self.return_items:
            if item.item_detail:
                item.item_detail.status = 'returned'
                item.item_detail.save()
                item.status = 'returned'
                item.save()

        # Update batch status
        self.status = 'confirmed'
        self.confirmed_by = user_id
        self.confirmed_at = datetime.utcnow()
        self.save()

        return True, f'Batch {self.batch_code} berhasil dikonfirmasi'

    def cancel(self, user_id, reason=None):
        """Cancel the return batch"""
        if self.status != 'pending':
            return False, 'Hanya batch dengan status pending yang dapat dibatalkan'

        # Update batch status
        self.status = 'cancelled'
        self.confirmed_by = user_id
        self.confirmed_at = datetime.utcnow()
        if reason:
            self.notes = f"{self.notes or ''}\n\nDibatalkan: {reason}"
        self.save()

        return True, f'Batch {self.batch_code} berhasil dibatalkan'

    @staticmethod
    def generate_batch_code(warehouse_id):
        """Generate unique batch code for return"""
        from app.models import Warehouse

        warehouse = Warehouse.query.get(warehouse_id)
        # Use warehouse ID since warehouse model doesn't have a 'code' field
        warehouse_code = f'WH{warehouse_id:03d}' if warehouse else 'WH000'

        # Get today's date in YYMMDD format
        today = datetime.now().strftime('%y%m%d')

        # Find existing batches for today
        existing_batches = ReturnBatch.query.filter(
            ReturnBatch.batch_code.like(f'RET-{warehouse_code}-{today}%')
        ).all()

        # Extract sequence numbers and find the highest
        sequences = []
        for batch in existing_batches:
            try:
                parts = batch.batch_code.split('-')
                if len(parts) == 4:
                    sequences.append(int(parts[3]))
            except (ValueError, IndexError):
                pass

        next_seq = max(sequences) + 1 if sequences else 1

        # Generate batch code: RET-{WAREHOUSE_CODE}-{YYMMDD}-{SEQUENCE}
        return f'RET-{warehouse_code}-{today}-{next_seq:03d}'


class ReturnItem(BaseModel):
    """ReturnItem model for individual items in a return batch"""
    __tablename__ = 'return_items'

    return_batch_id = db.Column(db.Integer, db.ForeignKey('return_batches.id'), nullable=False)
    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), nullable=True)

    return_reason = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, returned, cancelled
    notes = db.Column(db.Text)

    # Condition assessment
    condition = db.Column(db.String(50))  # good, damaged, broken, missing_parts
    condition_notes = db.Column(db.Text)

    # Relationships
    return_batch = db.relationship('ReturnBatch', back_populates='return_items')
    item_detail = db.relationship('ItemDetail', backref='return_items')
    unit = db.relationship('Unit', backref='return_items')
    distribution = db.relationship('Distribution', backref='return_items')

    def __repr__(self):
        return f'<ReturnItem Batch:{self.return_batch_id} Item:{self.item_detail_id}>'

    @property
    def condition_display(self):
        """Get display condition"""
        condition_map = {
            'good': 'Baik',
            'damaged': 'Rusak Ringan',
            'broken': 'Rusak Berat',
            'missing_parts': 'Hilang Komponen'
        }
        return condition_map.get(self.condition, self.condition)

    @property
    def status_display(self):
        """Get display status"""
        status_map = {
            'pending': 'Pending',
            'returned': 'Dikembalikan',
            'cancelled': 'Dibatalkan'
        }
        return status_map.get(self.status, self.status)
