"""
Add require_serial_number column to categories

This migration adds a 'require_serial_number' column to the categories table
to indicate whether items in this category require serial numbers.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add require_serial_number column to categories table"""
    app = create_app()

    with app.app_context():
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('categories')]

        if 'require_serial_number' not in columns:
            # Add the require_serial_number column with default value False
            db.session.execute(text("""
                ALTER TABLE categories
                ADD COLUMN require_serial_number BOOLEAN NOT NULL DEFAULT FALSE
            """))
            db.session.commit()

            print("✅ Column require_serial_number added to categories table")
        else:
            print("⚠️  Column require_serial_number already exists in categories table")

def downgrade():
    """Remove require_serial_number column from categories table"""
    app = create_app()

    with app.app_context():
        db.session.execute(text("""
            ALTER TABLE categories
            DROP COLUMN IF EXISTS require_serial_number
        """))
        db.session.commit()

        print("✅ Column require_serial_number removed from categories table")

if __name__ == '__main__':
    upgrade()
