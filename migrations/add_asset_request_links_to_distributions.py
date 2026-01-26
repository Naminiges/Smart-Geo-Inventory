"""
Migration: Add asset_request_id and asset_request_item_id to distributions table
This migration adds foreign key links to asset requests for tracking distribution source
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add asset_request links to distributions...")

        # Check if columns already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        if 'asset_request_id' in columns:
            print("Column asset_request_id already exists. Skipping migration.")
            return

        # Step 1: Add asset_request_id column
        print("\n1. Adding asset_request_id column...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            ADD COLUMN asset_request_id INTEGER;
        """))
        db.session.commit()
        print("   ✓ Column added successfully")

        # Step 2: Add asset_request_item_id column
        print("\n2. Adding asset_request_item_id column...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            ADD COLUMN asset_request_item_id INTEGER;
        """))
        db.session.commit()
        print("   ✓ Column added successfully")

        # Step 3: Add foreign key constraints
        print("\n3. Adding foreign key constraints...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            ADD CONSTRAINT fk_distributions_asset_request
            FOREIGN KEY (asset_request_id) REFERENCES asset_requests(id);
        """))
        db.session.commit()
        print("   ✓ Foreign key to asset_requests added")

        db.session.execute(db.text("""
            ALTER TABLE distributions
            ADD CONSTRAINT fk_distributions_asset_request_item
            FOREIGN KEY (asset_request_item_id) REFERENCES asset_request_items(id);
        """))
        db.session.commit()
        print("   ✓ Foreign key to asset_request_items added")

        # Step 4: Create indexes for better performance
        print("\n4. Creating indexes...")
        db.session.execute(db.text("""
            CREATE INDEX idx_distributions_asset_request_id ON distributions(asset_request_id);
        """))
        db.session.commit()
        print("   ✓ Index on distributions.asset_request_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_distributions_asset_request_item_id ON distributions(asset_request_item_id);
        """))
        db.session.commit()
        print("   ✓ Index on distributions.asset_request_item_id")

        print("\n✓ Migration completed successfully!")
        print("\nChanges:")
        print("- Added asset_request_id column to distributions table")
        print("- Added asset_request_item_id column to distributions table")
        print("- Added foreign key constraints")
        print("- Created indexes for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Remove asset_request links from distributions...")

        # Check if columns exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        if 'asset_request_id' not in columns and 'asset_request_item_id' not in columns:
            print("Columns do not exist. Nothing to rollback.")
            return

        # Drop indexes first
        print("\nDropping indexes...")
        try:
            db.session.execute(db.text("DROP INDEX IF EXISTS idx_distributions_asset_request_id;"))
            db.session.commit()
            print("   ✓ Index idx_distributions_asset_request_id dropped")
        except:
            pass

        try:
            db.session.execute(db.text("DROP INDEX IF EXISTS idx_distributions_asset_request_item_id;"))
            db.session.commit()
            print("   ✓ Index idx_distributions_asset_request_item_id dropped")
        except:
            pass

        # Drop foreign key constraints
        print("\nDropping foreign key constraints...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            DROP CONSTRAINT IF EXISTS fk_distributions_asset_request;
        """))
        db.session.commit()
        print("   ✓ Foreign key fk_distributions_asset_request dropped")

        db.session.execute(db.text("""
            ALTER TABLE distributions
            DROP CONSTRAINT IF EXISTS fk_distributions_asset_request_item;
        """))
        db.session.commit()
        print("   ✓ Foreign key fk_distributions_asset_request_item dropped")

        # Drop columns
        print("\nDropping columns...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            DROP COLUMN IF EXISTS asset_request_id;
        """))
        db.session.commit()
        print("   ✓ Column asset_request_id dropped")

        db.session.execute(db.text("""
            ALTER TABLE distributions
            DROP COLUMN IF EXISTS asset_request_item_id;
        """))
        db.session.commit()
        print("   ✓ Column asset_request_item_id dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for asset request links in distributions')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
