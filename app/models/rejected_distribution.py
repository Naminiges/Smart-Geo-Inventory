from datetime import datetime
from app import db
from app.models.base import BaseModel
from geoalchemy2 import Geometry


class RejectedDistribution(BaseModel):
    """Rejected Distribution model for storing history of rejected distributions"""
    __tablename__ = 'rejected_distributions'

    # Original distribution info
    original_distribution_id = db.Column(db.Integer, nullable=True)  # ID from distributions table
    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    field_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=True)
    address = db.Column(db.Text, nullable=False)
    geom = db.Column(Geometry('POINT', srid=4326))
    installed_at = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.Text)
    distribution_group_id = db.Column(db.Integer, db.ForeignKey('distribution_groups.id'), nullable=True)
    asset_request_id = db.Column(db.Integer, db.ForeignKey('asset_requests.id'), nullable=True)
    asset_request_item_id = db.Column(db.Integer, db.ForeignKey('asset_request_items.id'), nullable=True)

    # Draft information (when it was created)
    draft_created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    draft_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)  # When the original distribution was created

    # Rejection information
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rejected_at = db.Column(db.DateTime, nullable=False)  # When it was rejected
    rejection_reason = db.Column(db.Text)

    # Relationships
    item_detail = db.relationship('ItemDetail')
    warehouse = db.relationship('Warehouse')
    field_staff = db.relationship('User', foreign_keys=[field_staff_id])
    unit = db.relationship('Unit')
    unit_detail = db.relationship('UnitDetail')
    draft_creator = db.relationship('User', foreign_keys=[draft_created_by])
    rejector = db.relationship('User', foreign_keys=[rejected_by])
    distribution_group = db.relationship('DistributionGroup')

    def __repr__(self):
        return f'<RejectedDistribution {self.id} Item:{self.item_detail_id} Rejected:{self.rejected_at}>'

    @property
    def item_name(self):
        """Get item name for display"""
        if self.item_detail and self.item_detail.item:
            return self.item_detail.item.name
        return 'Unknown Item'

    @property
    def serial_number(self):
        """Get serial number for display"""
        if self.item_detail:
            return self.item_detail.serial_number
        return 'Unknown'

    @property
    def unit_name(self):
        """Get unit name for display"""
        if self.unit:
            return self.unit.name
        return 'Unknown Unit'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'original_distribution_id': self.original_distribution_id,
            'item_name': self.item_name,
            'serial_number': self.serial_number,
            'unit_name': self.unit_name,
            'address': self.address,
            'draft_created_by': self.draft_created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rejected_by': self.rejected_by,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'draft_notes': self.draft_notes
        }

    @staticmethod
    def create_from_distribution(distribution, user_id, reason=None):
        """Create a rejected distribution record from an existing distribution"""
        rejected = RejectedDistribution(
            original_distribution_id=distribution.id,
            item_detail_id=distribution.item_detail_id,
            warehouse_id=distribution.warehouse_id,
            field_staff_id=distribution.field_staff_id,
            unit_id=distribution.unit_id,
            unit_detail_id=distribution.unit_detail_id,
            address=distribution.address,
            geom=distribution.geom,
            installed_at=distribution.installed_at,
            note=distribution.note,
            distribution_group_id=distribution.distribution_group_id,
            asset_request_id=distribution.asset_request_id,
            asset_request_item_id=distribution.asset_request_item_id,
            draft_created_by=distribution.draft_created_by,
            draft_notes=distribution.draft_notes,
            created_at=distribution.created_at,
            rejected_by=user_id,
            rejected_at=datetime.utcnow(),
            rejection_reason=reason
        )
        rejected.save()
        return rejected
