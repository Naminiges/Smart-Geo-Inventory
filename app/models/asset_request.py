from datetime import datetime
from app import db
from app.models.base import BaseModel


class AssetRequestItem(BaseModel):
    """Individual item within an asset request"""
    __tablename__ = 'asset_request_items'

    asset_request_id = db.Column(db.Integer, db.ForeignKey('asset_requests.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    # Target location in unit
    unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=True)
    room_notes = db.Column(db.Text)  # Additional notes about room/location

    # Relationships
    asset_request = db.relationship('AssetRequest', backref='items')
    item = db.relationship('Item', backref='asset_request_items')
    unit_detail = db.relationship('UnitDetail', backref='asset_request_items')

    @property
    def item_name(self):
        """Get item name"""
        return self.item.name if self.item else 'Unknown'

    @property
    def target_location(self):
        """Get target location description"""
        if self.unit_detail:
            return f"{self.unit_detail.unit.name} - {self.unit_detail.room_name}"
        return self.room_notes or 'Not specified'

    def __repr__(self):
        return f'<AssetRequestItem #{self.id} {self.item.name if self.item else "N/A"} Qty:{self.quantity}>'


class AssetRequest(BaseModel):
    """Asset Request model for unit staff to request assets"""
    __tablename__ = 'asset_requests'

    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Verification tracking
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, verified, rejected, completed

    # Distribution tracking
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'))
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    received_at = db.Column(db.DateTime)

    # Notes
    request_notes = db.Column(db.Text)
    notes = db.Column(db.Text)

    # Relationships
    unit = db.relationship('Unit', backref='asset_requests')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='asset_requests_made')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='asset_requests_verified')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='asset_requests_received')
    distribution = db.relationship('Distribution', backref='asset_request')

    @property
    def total_quantity(self):
        """Get total quantity of all items in this request"""
        return sum(item.quantity for item in self.items) if self.items else 0

    @property
    def items_summary(self):
        """Get summary of items in this request"""
        if not self.items:
            return []

        summary = []
        for item in self.items:
            summary.append({
                'item_name': item.item.name if item.item else 'Unknown',
                'quantity': item.quantity,
                'location': item.target_location
            })
        return summary

    def verify(self, user_id, notes=None):
        """Verify asset request by admin"""
        if self.status != 'pending':
            return False, 'Hanya permohonan dengan status pending yang bisa diverifikasi'

        self.status = 'verified'
        self.verified_by = user_id
        self.verified_at = datetime.utcnow()
        if notes:
            self.verification_notes = notes
        self.save()
        return True, 'Permohonan aset berhasil diverifikasi'

    def reject(self, user_id, reason=None):
        """Reject asset request by admin"""
        if self.status != 'pending':
            return False, 'Hanya permohonan dengan status pending yang bisa ditolak'

        self.status = 'rejected'
        self.verified_by = user_id
        self.verified_at = datetime.utcnow()
        self.verification_notes = reason
        self.save()
        return True, 'Permohonan aset berhasil ditolak'

    def mark_completed(self, distribution_id, user_id):
        """Mark asset request as completed after distribution"""
        if self.status != 'verified':
            return False, 'Hanya permohonan yang sudah diverifikasi yang bisa diselesaikan'

        self.status = 'completed'
        self.distribution_id = distribution_id
        self.received_by = user_id
        self.received_at = datetime.utcnow()
        self.save()
        return True, 'Permohonan aset berhasil diselesaikan'

    def __repr__(self):
        return f'<AssetRequest #{self.id} Unit:{self.unit.name if self.unit else "N/A"} Status:{self.status}>'
