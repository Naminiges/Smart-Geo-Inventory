#!/usr/bin/env python3
"""
Migration script to add created_at and updated_at columns to user_warehouses table
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """Add created_at and updated_at columns if they don't exist"""
    app = create_app()

    with app.app_context():
        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user_warehouses')]

        # Add created_at if not exists
        if 'created_at' not in columns:
            print("Adding 'created_at' column to user_warehouses table...")
            db.session.execute(text("""
                ALTER TABLE user_warehouses
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            print("✓ created_at column added")
        else:
            print("✓ Column 'created_at' already exists")

        # Add updated_at if not exists
        if 'updated_at' not in columns:
            print("Adding 'updated_at' column to user_warehouses table...")
            db.session.execute(text("""
                ALTER TABLE user_warehouses
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            print("✓ updated_at column added")
        else:
            print("✓ Column 'updated_at' already exists")

        db.session.commit()
        print("\n✓ Migration completed successfully!")

def rollback():
    """Remove created_at and updated_at columns (USE WITH CAUTION)"""
    app = create_app()

    with app.app_context():
        confirm = input("⚠️  WARNING: This will DROP created_at and updated_at columns! Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Rollback cancelled.")
            return

        print("Dropping columns from user_warehouses table...")

        # Drop columns
        db.session.execute(text("ALTER TABLE user_warehouses DROP COLUMN IF EXISTS created_at"))
        db.session.execute(text("ALTER TABLE user_warehouses DROP COLUMN IF EXISTS updated_at"))

        db.session.commit()
        print("✓ Rollback completed!")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for user_warehouses timestamp columns')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration (drop columns)')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
