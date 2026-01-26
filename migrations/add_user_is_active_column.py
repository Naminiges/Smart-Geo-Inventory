"""
Migration: Add is_active column to users table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add is_active column to users table...")

        try:
            # Add is_active column
            print("\nAdding is_active column to users table...")
            db.session.execute(db.text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;
            """))
            db.session.commit()
            print("   [OK] Column 'is_active' added successfully")

            # Update existing rows to have True value
            print("\nUpdating existing rows...")
            db.session.execute(db.text("""
                UPDATE users
                SET is_active = TRUE
                WHERE is_active IS NULL;
            """))
            db.session.commit()
            print("   [OK] Existing rows updated")

            print("\n[OK] Migration completed successfully!")
            print("\nColumn 'is_active' added to users table with default value TRUE")

        except Exception as e:
            print(f"\n[ERROR] Error during migration: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrate()
