from datetime import datetime
from app import db
from app.models.base import BaseModel


class DistributionGroup(BaseModel):
    """Distribution Group model for batch distribution management"""
    __tablename__ = 'distribution_groups'

    # Group identification
    name = db.Column(db.String(255), nullable=False)  # Optional: batch name/description
    batch_code = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Unique batch code

    # Group metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Who created this batch
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)  # Source warehouse
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)  # Destination unit

    # Verification fields
    is_draft = db.Column(db.Boolean, default=True, nullable=False, index=True)  # True = pending verification
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who verified
    verified_at = db.Column(db.DateTime)  # When verified
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who rejected
    rejected_at = db.Column(db.DateTime)  # When rejected
    rejection_reason = db.Column(db.Text)  # Reason for rejection
    notes = db.Column(db.Text)  # Notes from creator

    # Status tracking
    status = db.Column(db.String(50), default='pending', index=True)  # pending, approved, rejected, distributed

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_distribution_groups')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_distribution_groups')
    rejector = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_distribution_groups')
    warehouse = db.relationship('Warehouse', backref='distribution_groups')
    unit = db.relationship('Unit', backref='distribution_groups')
    distributions = db.relationship('Distribution', back_populates='distribution_group', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DistributionGroup {self.batch_code} Status:{self.status}>'

    def approve(self, user_id):
        """Approve the distribution group and all its distributions"""
        if not self.is_draft:
            return False, 'Batch ini sudah diproses'

        # Update group status
        self.is_draft = False
        self.status = 'approved'
        self.verified_by = user_id
        self.verified_at = datetime.utcnow()
        self.save()

        # Approve all distributions in this group
        for distribution in self.distributions:
            if distribution.is_draft:
                distribution.verify_draft(user_id)

        return True, f'Batch {self.batch_code} berhasil disetujui'

    def reject(self, user_id, reason=None):
        """Reject the distribution group and all its distributions (keep records for history)"""
        if not self.is_draft:
            return False, 'Batch ini sudah diproses'

        # Update group status
        self.is_draft = False
        self.status = 'rejected'
        self.rejected_by = user_id
        self.rejected_at = datetime.utcnow()
        self.rejection_reason = reason
        self.save()

        # Reject all distributions in this group (will keep records)
        for distribution in self.distributions:
            if distribution.is_draft:
                distribution.reject_draft(user_id, reason)

        return True, f'Batch {self.batch_code} ({len(self.distributions)} barang) berhasil ditolak'

    def mark_distributed(self):
        """Mark the group as fully distributed"""
        self.status = 'distributed'
        self.save()

    @property
    def total_items(self):
        """Get total number of items in this group"""
        return len(self.distributions)

    @property
    def status_display(self):
        """Get display status"""
        status_map = {
            'pending': 'Menunggu Verifikasi',
            'approved': 'Disetujui',
            'rejected': 'Ditolak',
            'distributed': 'Sedang Didistribusikan'
        }
        return status_map.get(self.status, self.status)

    @staticmethod
    def generate_batch_code():
        """Generate unique batch code"""
        import uuid
        return str(uuid.uuid4())[:8].upper()
