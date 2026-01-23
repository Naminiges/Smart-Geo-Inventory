"""
Migration: Create venue_loans table

This migration creates a table for venue/room borrowing requests where units can
borrow rooms from other units for events.

Author: System
Date: 2025-01-23
"""

from datetime import datetime
from app import create_app, db
from app.models.venue_loan import VenueLoan


def upgrade():
    """Create the venue_loans table"""
    # Create table using SQLAlchemy models
    VenueLoan.__table__.create(db.engine, checkfirst=True)
    print("venue_loans table created successfully!")


def downgrade():
    """Drop the venue_loans table"""
    VenueLoan.__table__.drop(db.engine, checkfirst=True)
    print("venue_loans table dropped successfully!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        upgrade()
