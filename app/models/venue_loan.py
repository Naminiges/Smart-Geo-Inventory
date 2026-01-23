from datetime import datetime
from app import db
from app.models.base import BaseModel
from app.utils.datetime_helper import get_wib_now


class VenueLoan(BaseModel):
    """Venue Loan model for borrowing rooms/venues within units"""
    __tablename__ = 'venue_loans'

    unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=False)
    borrower_unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    borrower_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Loan details
    event_name = db.Column(db.String(200), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)

    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, approved, active, completed, rejected
    # pending: menunggu persetujuan admin
    # approved: disetujui admin, menunggu waktu mulai (barang masih used)
    # active: sedang berlangsung dalam rentang waktu (barang jadi loaned/Dipinjam)
    # completed: waktu selesai, barang kembali terpakai
    # rejected: ditolak admin

    # Approval tracking
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Completion tracking (when time finishes)
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    completed_at = db.Column(db.DateTime)

    # Relationships
    unit_detail = db.relationship('UnitDetail', backref='venue_loans')
    borrower_unit = db.relationship('Unit', foreign_keys=[borrower_unit_id], backref='borrowed_venue_loans')
    borrower_user = db.relationship('User', foreign_keys=[borrower_user_id], backref='requested_venue_loans')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_venue_loans')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_venue_loans')

    @property
    def status_display(self):
        """Get display status"""
        status_map = {
            'pending': 'Pending',
            'approved': 'Disetujui',
            'active': 'Dipinjam',
            'completed': 'Selesai',
            'rejected': 'Ditolak'
        }
        return status_map.get(self.status, self.status)

    @property
    def status_badge_class(self):
        """Get badge class for status"""
        class_map = {
            'pending': 'bg-yellow-100 text-yellow-700',
            'approved': 'bg-green-100 text-green-700',
            'active': 'bg-purple-100 text-purple-700',
            'completed': 'bg-gray-100 text-gray-700',
            'rejected': 'bg-red-100 text-red-700'
        }
        return class_map.get(self.status, 'bg-gray-100 text-gray-700')

    @property
    def is_time_expired(self):
        """Check if loan time has expired"""
        if self.status != 'active':
            return False
        return get_wib_now() > self.end_datetime

    def approve(self, user_id):
        """Approve venue loan request - wait for start time to begin loaning"""
        if self.status != 'pending':
            return False, 'Hanya permohonan dengan status pending yang dapat disetujui'

        self.status = 'approved'
        self.approved_by = user_id
        self.approved_at = get_wib_now()
        self.save()

        # Items remain in 'used' status until start time
        return True, 'Peminjaman tempat berhasil disetujui'

    def start_loan(self):
        """Start the loan when start time is reached - items become loaned"""
        if self.status != 'approved':
            return False, 'Status tidak valid untuk memulai peminjaman'

        # Check if start time has been reached (compare WIB with WIB)
        if get_wib_now() < self.start_datetime:
            return False, 'Waktu mulai belum tercapai'

        self.status = 'active'
        self.save()

        # Update all items in the room to loaned status
        self._update_room_items_status('loaned', f'Dipinjam - {self.borrower_unit.name}')

        return True, 'Peminjaman dimulai, barang berstatus Dipinjam'

    def reject(self, user_id, reason=None):
        """Reject venue loan request"""
        if self.status != 'pending':
            return False, 'Hanya permohonan dengan status pending yang dapat ditolak'

        self.status = 'rejected'
        self.approved_by = user_id
        self.approved_at = get_wib_now()
        self.rejection_reason = reason
        self.save()

        return True, 'Peminjaman tempat ditolak'

    def complete(self, user_id=None, auto=False):
        """Complete the loan after time expires - restore to used status

        Args:
            user_id: ID of admin who manually completes (optional for auto-complete)
            auto: True if called by scheduler automatically
        """
        if self.status != 'active':
            return False, 'Hanya peminjaman dengan status aktif yang dapat diselesaikan'

        # Restore all items in the room to used status
        self._update_room_items_status('used')

        self.status = 'completed'
        if user_id:
            self.completed_by = user_id
        self.completed_at = get_wib_now()
        self.save()

        return True, 'Peminjaman selesai, status barang dikembalikan ke terpakai'

    def _update_room_items_status(self, new_status, notes=None):
        """Update all items in the room to a new status"""
        from app.models import Distribution, ItemDetail

        # Get all distributions in this room
        distributions = Distribution.query.filter_by(unit_detail_id=self.unit_detail_id).all()

        for dist in distributions:
            if dist.item_detail:
                dist.item_detail.status = new_status
                # Optionally add notes
                if notes:
                    if not dist.item_detail.specification_notes:
                        dist.item_detail.specification_notes = notes
                    else:
                        dist.item_detail.specification_notes += f' | {notes}'
                dist.item_detail.save()

    def __repr__(self):
        return f'<VenueLoan #{self.id} {self.event_name} Status:{self.status}>'
