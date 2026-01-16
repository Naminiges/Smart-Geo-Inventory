from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.base import BaseModel


class User(UserMixin, BaseModel):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin | warehouse_staff | field_staff
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))  # ONLY for warehouse_staff

    # Relationships
    warehouse = db.relationship('Warehouse', back_populates='users')
    user_warehouses = db.relationship('UserWarehouse', back_populates='user', lazy='dynamic')
    distributions = db.relationship('Distribution', foreign_keys='Distribution.field_staff_id', back_populates='field_staff')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_warehouse_staff(self):
        """Check if user is warehouse staff"""
        return self.role == 'warehouse_staff'

    def is_field_staff(self):
        """Check if user is field staff"""
        return self.role == 'field_staff'

    def get_accessible_warehouses(self):
        """Get list of warehouses this user can access"""
        if self.is_admin():
            from app.models import Warehouse
            return Warehouse.query.all()
        elif self.is_warehouse_staff() or self.is_field_staff():
            # Get warehouses from UserWarehouse assignments
            return [uw.warehouse for uw in self.user_warehouses.all()]
        else:
            return []

    def has_warehouse_access(self, warehouse_id):
        """Check if user has access to specific warehouse"""
        if self.is_admin():
            return True

        # Check if warehouse is in user's assignments
        return any(uw.warehouse_id == warehouse_id for uw in self.user_warehouses.all())

    def __repr__(self):
        return f'<User {self.email} - {self.role}>'


class UserWarehouse(BaseModel):
    """User-Warehouse many-to-many relationship"""
    __tablename__ = 'user_warehouses'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='user_warehouses')
    warehouse = db.relationship('Warehouse')

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'warehouse_id', name='unique_user_warehouse'),
    )

    def __repr__(self):
        return f'<UserWarehouse User:{self.user_id} Warehouse:{self.warehouse_id}>'
