"""
Migration: Add status column to units table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add status column to units table...")

        try:
            # Add status column
            print("\nAdding status column to units table...")
            db.session.execute(db.text("""
                ALTER TABLE units
                ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'available';
            """))
            db.session.commit()
            print("   ✓ Column 'status' added successfully")

            # Update existing rows to have 'available' status
            print("\nUpdating existing rows...")
            db.session.execute(db.text("""
                UPDATE units
                SET status = 'available'
                WHERE status IS NULL;
            """))
            db.session.commit()
            print("   ✓ Existing rows updated")

            print("\n✓ Migration completed successfully!")
            print("\nColumn 'status' added to units table with default value 'available'")

        except Exception as e:
            print(f"\n✗ Error during migration: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrate()
