"""
Migration: Add status and distribution_id to asset_request_items table
This migration adds tracking fields for distribution workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add status and distribution_id to asset_request_items...")

        # Check if columns already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('asset_request_items')]

        if 'status' in columns:
            print("Column status already exists. Skipping migration.")
            return

        # Step 1: Add status column
        print("\n1. Adding status column...")
        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            ADD COLUMN status VARCHAR(20) DEFAULT 'pending' NOT NULL;
        """))
        db.session.commit()
        print("   ✓ Column added successfully")

        # Step 2: Add distribution_id column
        print("\n2. Adding distribution_id column...")
        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            ADD COLUMN distribution_id INTEGER;
        """))
        db.session.commit()
        print("   ✓ Column added successfully")

        # Step 3: Add foreign key constraint
        print("\n3. Adding foreign key constraint...")
        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            ADD CONSTRAINT fk_asset_request_items_distribution
            FOREIGN KEY (distribution_id) REFERENCES distributions(id);
        """))
        db.session.commit()
        print("   ✓ Foreign key to distributions added")

        # Step 4: Create index
        print("\n4. Creating index...")
        db.session.execute(db.text("""
            CREATE INDEX idx_asset_request_items_distribution_id ON asset_request_items(distribution_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_request_items.distribution_id")

        print("\n✓ Migration completed successfully!")
        print("\nChanges:")
        print("- Added status column to asset_request_items table")
        print("- Added distribution_id column to asset_request_items table")
        print("- Added foreign key constraint")
        print("- Created index for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Remove status and distribution_id from asset_request_items...")

        # Check if columns exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('asset_request_items')]

        if 'status' not in columns and 'distribution_id' not in columns:
            print("Columns do not exist. Nothing to rollback.")
            return

        # Drop index first
        print("\nDropping index...")
        try:
            db.session.execute(db.text("DROP INDEX IF EXISTS idx_asset_request_items_distribution_id;"))
            db.session.commit()
            print("   ✓ Index dropped")
        except:
            pass

        # Drop foreign key constraint
        print("\nDropping foreign key constraint...")
        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            DROP CONSTRAINT IF EXISTS fk_asset_request_items_distribution;
        """))
        db.session.commit()
        print("   ✓ Foreign key dropped")

        # Drop columns
        print("\nDropping columns...")
        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            DROP COLUMN IF EXISTS status;
        """))
        db.session.commit()
        print("   ✓ Column status dropped")

        db.session.execute(db.text("""
            ALTER TABLE asset_request_items
            DROP COLUMN IF EXISTS distribution_id;
        """))
        db.session.commit()
        print("   ✓ Column distribution_id dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for asset request item status')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
