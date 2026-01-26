"""
Migration: Add profile_image column to users table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add profile_image column to users table...")

        try:
            # Add profile_image column
            print("\nAdding profile_image column to users table...")
            db.session.execute(db.text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS profile_image VARCHAR(255);
            """))
            db.session.commit()
            print("   [OK] Column 'profile_image' added successfully")

            print("\n[OK] Migration completed successfully!")
            print("\nColumn 'profile_image' added to users table")

        except Exception as e:
            print(f"\n[ERROR] Error during migration: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrate()
