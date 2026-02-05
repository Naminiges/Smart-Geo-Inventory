from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import db


class BaseModel(db.Model):
    """Base model with common fields and methods"""
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        """Save model to database"""
        try:
            # Only add if not already in session (for new records)
            # This prevents SQLAlchemy from setting nullable fields to None on update
            if self not in db.session:
                db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        """Delete model from database"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, id):
        """Get model by ID"""
        return cls.query.get(id)

    @classmethod
    def get_all(cls):
        """Get all models"""
        return cls.query.all()

    def to_dict(self):
        """Convert model to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"
