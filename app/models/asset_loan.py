from datetime import datetime
from app import db
from app.models.base import BaseModel


class AssetLoanItem(BaseModel):
    """Individual item within an asset loan request"""
    __tablename__ = 'asset_loan_items'

    asset_loan_id = db.Column(db.Integer, db.ForeignKey('asset_loans.id'), nullable=False)
    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Temporary new item data (if item doesn't exist yet)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    item_name = db.Column(db.String(200))

    # Return tracking
    return_status = db.Column(db.String(50), default='borrowed')  # borrowed, returned, return_requested
    return_date = db.Column(db.DateTime)
    return_notes = db.Column(db.Text)
    return_photo = db.Column(db.String(500))  # Path to uploaded return proof photo
    return_verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    return_verified_at = db.Column(db.DateTime)
    return_verification_status = db.Column(db.String(50), default='pending')  # pending, submitted, verified, rejected
    return_rejection_reason = db.Column(db.Text)

    # Relationships
    asset_loan = db.relationship('AssetLoan', back_populates='items')
    item_detail = db.relationship('ItemDetail', backref='asset_loan_items')
    item = db.relationship('Item', backref='asset_loan_items')
    return_verifier = db.relationship('User', foreign_keys=[return_verified_by], backref='verified_asset_loan_items')

    def __repr__(self):
        return f'<AssetLoanItem #{self.id} Qty:{self.quantity} Status:{self.return_status}>'


class AssetLoan(BaseModel):
    """Asset loan model for borrowing/lending general assets"""
    __tablename__ = 'asset_loans'

    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, approved, shipped, received, active, completed, cancelled, returned
    # pending: menunggu persetujuan warehouse
    # approved: disetujui warehouse, menunggu pengiriman
    # shipped: sedang dikirim ke unit
    # received: unit menerima barang
    # active: barang sedang dipakai unit
    # completed: peminjaman selesai (barang sudah dikembalikan dan diverifikasi)
    # cancelled: dibatalkan
    # returned: dalam proses retur

    # Request tracking
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    request_notes = db.Column(db.Text)  # Alasan permohonan

    # Approval tracking
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text)

    # Shipment tracking
    shipped_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    shipped_at = db.Column(db.DateTime)
    shipment_notes = db.Column(db.Text)

    # Receipt tracking (when unit receives the items)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    received_at = db.Column(db.DateTime)
    receipt_notes = db.Column(db.Text)

    # Completion/return tracking
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    completed_at = db.Column(db.DateTime)
    completion_notes = db.Column(db.Text)

    # Return request tracking
    return_requested_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    return_requested_at = db.Column(db.DateTime)
    return_reason = db.Column(db.Text)
    return_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    return_approved_at = db.Column(db.DateTime)
    return_notes = db.Column(db.Text)

    # Relationships
    unit = db.relationship('Unit', backref='asset_loans')
    warehouse = db.relationship('Warehouse', backref='asset_loans')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_asset_loans')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_asset_loans')
    shipper = db.relationship('User', foreign_keys=[shipped_by], backref='shipped_asset_loans')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='received_asset_loans')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_asset_loans')
    return_requester = db.relationship('User', foreign_keys=[return_requested_by], backref='return_requested_asset_loans')
    return_approver = db.relationship('User', foreign_keys=[return_approved_by], backref='return_approved_asset_loans')
    items = db.relationship('AssetLoanItem', back_populates='asset_loan', cascade='all, delete-orphan')

    @property
    def total_quantity(self):
        """Get total quantity of all items in this loan"""
        return sum(item.quantity for item in self.items) if self.items else 0

    @property
    def total_returned(self):
        """Get total quantity of returned items"""
        return sum(item.quantity for item in self.items if item.return_status in ['returned']) if self.items else 0

    @property
    def is_fully_returned(self):
        """Check if all items have been returned"""
        if not self.items:
            return False
        return all(item.return_status in ['returned'] for item in self.items)

    def get_status_display(self):
        """Get human-readable status display"""
        status_map = {
            'pending': 'Menunggu Persetujuan',
            'approved': 'Disetujui',
            'shipped': 'Sedang Dikirim',
            'received': 'Diterima Unit',
            'active': 'Sedang Dipakai',
            'completed': 'Selesai',
            'cancelled': 'Dibatalkan',
            'returned': 'Dalam Proses Retur'
        }
        return status_map.get(self.status, self.status)

    def approve(self, user_id, notes=None):
        """Approve loan request (warehouse action)"""
        if self.status != 'pending':
            return False, 'Hanya permohonan dengan status pending yang bisa disetujui'

        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.utcnow()
        self.approval_notes = notes
        self.save()
        return True, 'Permohonan peminjaman berhasil disetujui'

    def reject(self, user_id, reason=None):
        """Reject loan request (warehouse action)"""
        if self.status not in ['pending', 'approved']:
            return False, 'Tidak bisa menolak permohonan yang sudah diproses'

        self.status = 'cancelled'
        self.approved_by = user_id
        self.approval_date = datetime.utcnow()
        self.approval_notes = reason
        self.save()
        return True, 'Permohonan peminjaman berhasil ditolak'

    def ship(self, user_id, notes=None):
        """Mark loan as shipped (warehouse action)"""
        if self.status != 'approved':
            return False, 'Hanya permohonan yang sudah disetujui yang bisa dikirim'

        # Update item detail status to processing
        for item in self.items:
            if item.item_detail:
                item.item_detail.status = 'processing'
                item.item_detail.save()

        self.status = 'shipped'
        self.shipped_by = user_id
        self.shipped_at = datetime.utcnow()
        self.shipment_notes = notes
        self.save()
        return True, 'Barang berhasil dikirim ke unit'

    def receive_by_unit(self, user_id, notes=None):
        """Mark loan as received by unit (unit action)"""
        if self.status != 'shipped':
            return False, 'Tidak bisa menerima barang dengan status ini'

        self.status = 'active'
        self.received_by = user_id
        self.received_at = datetime.utcnow()
        self.receipt_notes = notes
        self.save()
        return True, 'Barang berhasil diterima. Peminjaman aktif.'

    def request_return(self, user_id, reason=None):
        """Request return of loaned items (unit action)"""
        if self.status != 'active':
            return False, 'Hanya peminjaman aktif yang bisa diajukan retur'

        self.status = 'returned'
        self.return_requested_by = user_id
        self.return_requested_at = datetime.utcnow()
        self.return_reason = reason
        self.save()
        return True, 'Permohonan retur berhasil diajukan'

    def approve_return(self, user_id, notes=None):
        """Approve return request (warehouse action)"""
        if self.status != 'returned':
            return False, 'Tidak ada permohonan retur untuk disetujui'

        self.status = 'pending_return_verification'
        self.return_approved_by = user_id
        self.return_approved_at = datetime.utcnow()
        self.return_notes = notes
        self.save()
        return True, 'Permohonan retur disetujui. Menunggu verifikasi bukti pengembalian.'

    def verify_return_item(self, item_id, user_id, approve=True, reason=None):
        """Verify return of individual item (warehouse action)"""
        item = AssetLoanItem.query.get(item_id)
        if not item or item.asset_loan_id != self.id:
            return False, 'Item tidak ditemukan'

        if item.return_verification_status == 'verified':
            return False, 'Item sudah diverifikasi'

        if approve:
            item.return_verification_status = 'verified'
            item.return_verified_by = user_id
            item.return_verified_at = datetime.utcnow()
            item.return_status = 'returned'

            # Update item detail status back to available
            if item.item_detail:
                item.item_detail.status = 'available'
                item.item_detail.save()

            item.save()

            # Check if all items are returned
            if self.is_fully_returned:
                self.status = 'completed'
                self.completed_by = user_id
                self.completed_at = datetime.utcnow()
                self.save()

            return True, 'Item berhasil diverifikasi'
        else:
            item.return_verification_status = 'rejected'
            item.return_rejection_reason = reason
            item.return_verified_by = user_id
            item.return_verified_at = datetime.utcnow()
            item.save()
            return True, 'Pengembalian item ditolak'

    def __repr__(self):
        return f'<AssetLoan #{self.id} Unit:{self.unit.name if self.unit else "N/A"} Status:{self.status}>'
