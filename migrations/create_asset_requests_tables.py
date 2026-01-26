"""
Migration: Create asset_requests and asset_request_items tables
This migration creates tables for asset request system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Create asset_requests tables...")

        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'asset_requests' in tables:
            print("Table asset_requests already exists. Skipping migration.")
            return

        # Step 1: Create asset_requests table
        print("\n1. Creating asset_requests table...")
        db.session.execute(db.text("""
            CREATE TABLE asset_requests (
                id SERIAL PRIMARY KEY,
                unit_id INTEGER NOT NULL,
                requested_by INTEGER NOT NULL,
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by INTEGER,
                verified_at TIMESTAMP,
                verification_notes TEXT,
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                distribution_id INTEGER,
                received_by INTEGER,
                received_at TIMESTAMP,
                request_notes TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (requested_by) REFERENCES users(id),
                FOREIGN KEY (verified_by) REFERENCES users(id),
                FOREIGN KEY (distribution_id) REFERENCES distributions(id),
                FOREIGN KEY (received_by) REFERENCES users(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 2: Create asset_request_items table
        print("\n2. Creating asset_request_items table...")
        db.session.execute(db.text("""
            CREATE TABLE asset_request_items (
                id SERIAL PRIMARY KEY,
                asset_request_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_detail_id INTEGER,
                room_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_request_id) REFERENCES asset_requests(id),
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (unit_detail_id) REFERENCES unit_details(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 3: Create indexes for better performance
        print("\n3. Creating indexes...")
        db.session.execute(db.text("""
            CREATE INDEX idx_asset_requests_unit_id ON asset_requests(unit_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_requests.unit_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_requests_status ON asset_requests(status);
        """))
        db.session.commit()
        print("   ✓ Index on asset_requests.status")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_requests_requested_by ON asset_requests(requested_by);
        """))
        db.session.commit()
        print("   ✓ Index on asset_requests.requested_by")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_request_items_request_id ON asset_request_items(asset_request_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_request_items.asset_request_id")

        print("\n✓ Migration completed successfully!")
        print("\nTables created:")
        print("- asset_requests: Header permohonan aset")
        print("- asset_request_items: Detail items dalam permohonan")
        print("\nIndexes created for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Drop asset_requests tables...")

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'asset_request_items' not in tables and 'asset_requests' not in tables:
            print("Tables do not exist. Nothing to rollback.")
            return

        # Drop in correct order (child first)
        if 'asset_request_items' in tables:
            print("\nDropping asset_request_items table...")
            db.session.execute(db.text("DROP TABLE asset_request_items;"))
            db.session.commit()
            print("   ✓ Table dropped")

        if 'asset_requests' in tables:
            print("\nDropping asset_requests table...")
            db.session.execute(db.text("DROP TABLE asset_requests;"))
            db.session.commit()
            print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for asset_requests tables')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
