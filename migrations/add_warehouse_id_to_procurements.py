"""
Add warehouse_id column to procurements table
This allows procurement to be assigned to a specific warehouse
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add warehouse_id column to procurements table"""
    app = create_app()

    with app.app_context():
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('procurements')]

        if 'warehouse_id' not in columns:
            # Add the column
            db.session.execute(text("""
                ALTER TABLE procurements
                ADD COLUMN warehouse_id INTEGER REFERENCES warehouses(id)
            """))
            db.session.commit()

            print("✅ Column warehouse_id added to procurements table")
        else:
            print("⚠️  Column warehouse_id already exists in procurements table")

def downgrade():
    """Remove warehouse_id column from procurements table"""
    app = create_app()

    with app.app_context():
        db.session.execute(text("""
            ALTER TABLE procurements
            DROP COLUMN IF EXISTS warehouse_id
        """))
        db.session.commit()

        print("✅ Column warehouse_id removed from procurements table")

if __name__ == '__main__':
    upgrade()
