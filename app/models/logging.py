from datetime import datetime
from app import db
from app.models.base import BaseModel


class ActivityLog(BaseModel):
    """Activity log for tracking all changes in the system"""
    __tablename__ = 'activity_logs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(100))
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    old_data = db.Column(db.JSON)  # JSONB in PostgreSQL
    new_data = db.Column(db.JSON)  # JSONB in PostgreSQL
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = db.relationship('User')

    @classmethod
    def log_activity(cls, user, action, table_name, record_id=None, old_data=None, new_data=None, ip_address=None):
        """Create a new activity log entry"""
        log = cls(
            user_id=user.id if user else None,
            username=user.name if user else 'System',
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_data=old_data,
            new_data=new_data,
            ip_address=ip_address
        )
        log.save()
        return log

    def __repr__(self):
        return f'<ActivityLog {self.action} on {self.table_name} by {self.username}>'


class AssetMovementLog(BaseModel):
    """Asset movement log for tracking physical item movements"""
    __tablename__ = 'asset_movement_logs'

    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'))
    serial_number = db.Column(db.String(100))
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    operator_name = db.Column(db.String(100))
    origin_type = db.Column(db.String(50))  # warehouse, unit, etc.
    origin_id = db.Column(db.Integer)
    destination_type = db.Column(db.String(50))  # warehouse, unit, etc.
    destination_id = db.Column(db.Integer)
    status_before = db.Column(db.String(50))
    status_after = db.Column(db.String(50))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    item_detail = db.relationship('ItemDetail')
    operator = db.relationship('User')

    @classmethod
    def log_movement(cls, item_detail, operator, origin_type, origin_id, destination_type, destination_id, status_before, status_after, note=None):
        """Create a new asset movement log entry"""
        log = cls(
            item_detail_id=item_detail.id if item_detail else None,
            serial_number=item_detail.serial_number if item_detail else None,
            operator_id=operator.id if operator else None,
            operator_name=operator.name if operator else 'System',
            origin_type=origin_type,
            origin_id=origin_id,
            destination_type=destination_type,
            destination_id=destination_id,
            status_before=status_before,
            status_after=status_after,
            note=note
        )
        log.save()
        return log

    def __repr__(self):
        return f'<AssetMovementLog {self.serial_number} from {self.origin_type} to {self.destination_type}>'
