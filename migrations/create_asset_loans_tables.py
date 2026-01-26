"""
Migration: Create asset_loans and asset_loan_items tables
This migration creates tables for asset loan/borrowing system (Aset Umum)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Create asset_loans tables...")

        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'asset_loans' in tables:
            print("Table asset_loans already exists. Skipping migration.")
            return

        # Step 1: Create asset_loans table
        print("\n1. Creating asset_loans table...")
        db.session.execute(db.text("""
            CREATE TABLE asset_loans (
                id SERIAL PRIMARY KEY,
                unit_id INTEGER NOT NULL,
                warehouse_id INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                requested_by INTEGER NOT NULL,
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_notes TEXT,
                approved_by INTEGER,
                approval_date TIMESTAMP,
                approval_notes TEXT,
                shipped_by INTEGER,
                shipped_at TIMESTAMP,
                shipment_notes TEXT,
                received_by INTEGER,
                received_at TIMESTAMP,
                receipt_notes TEXT,
                completed_by INTEGER,
                completed_at TIMESTAMP,
                completion_notes TEXT,
                return_requested_by INTEGER,
                return_requested_at TIMESTAMP,
                return_reason TEXT,
                return_approved_by INTEGER,
                return_approved_at TIMESTAMP,
                return_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
                FOREIGN KEY (requested_by) REFERENCES users(id),
                FOREIGN KEY (approved_by) REFERENCES users(id),
                FOREIGN KEY (shipped_by) REFERENCES users(id),
                FOREIGN KEY (received_by) REFERENCES users(id),
                FOREIGN KEY (completed_by) REFERENCES users(id),
                FOREIGN KEY (return_requested_by) REFERENCES users(id),
                FOREIGN KEY (return_approved_by) REFERENCES users(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 2: Create asset_loan_items table
        print("\n2. Creating asset_loan_items table...")
        db.session.execute(db.text("""
            CREATE TABLE asset_loan_items (
                id SERIAL PRIMARY KEY,
                asset_loan_id INTEGER NOT NULL,
                item_detail_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                item_id INTEGER,
                item_name VARCHAR(200),
                return_status VARCHAR(50) DEFAULT 'borrowed',
                return_date TIMESTAMP,
                return_notes TEXT,
                return_photo VARCHAR(500),
                return_verified_by INTEGER,
                return_verified_at TIMESTAMP,
                return_verification_status VARCHAR(50) DEFAULT 'pending',
                return_rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_loan_id) REFERENCES asset_loans(id),
                FOREIGN KEY (item_detail_id) REFERENCES item_details(id),
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (return_verified_by) REFERENCES users(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 3: Create indexes for better performance
        print("\n3. Creating indexes...")

        # Indexes for asset_loans
        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loans_unit_id ON asset_loans(unit_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loans.unit_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loans_warehouse_id ON asset_loans(warehouse_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loans.warehouse_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loans_status ON asset_loans(status);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loans.status")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loans_requested_by ON asset_loans(requested_by);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loans.requested_by")

        # Indexes for asset_loan_items
        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loan_items_loan_id ON asset_loan_items(asset_loan_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loan_items.asset_loan_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loan_items_item_detail_id ON asset_loan_items(item_detail_id);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loan_items.item_detail_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_asset_loan_items_return_status ON asset_loan_items(return_status);
        """))
        db.session.commit()
        print("   ✓ Index on asset_loan_items.return_status")

        print("\n✓ Migration completed successfully!")
        print("\nTables created:")
        print("- asset_loans: Header peminjaman aset")
        print("- asset_loan_items: Detail items dalam peminjaman")
        print("\nIndexes created for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Drop asset_loans tables...")

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'asset_loan_items' not in tables and 'asset_loans' not in tables:
            print("Tables do not exist. Nothing to rollback.")
            return

        # Drop in correct order (child first)
        if 'asset_loan_items' in tables:
            print("\nDropping asset_loan_items table...")
            db.session.execute(db.text("DROP TABLE asset_loan_items;"))
            db.session.commit()
            print("   ✓ Table dropped")

        if 'asset_loans' in tables:
            print("\nDropping asset_loans table...")
            db.session.execute(db.text("DROP TABLE asset_loans;"))
            db.session.commit()
            print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for asset_loans tables')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
