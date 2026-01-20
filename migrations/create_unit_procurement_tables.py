"""
Migration: Create unit_procurements and unit_procurement_items tables
This migration creates tables for unit procurement request system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Create unit_procurements tables...")

        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'unit_procurements' in tables:
            print("Table unit_procurements already exists. Skipping migration.")
            return

        # Step 1: Create unit_procurements table
        print("\n1. Creating unit_procurements table...")
        db.session.execute(db.text("""
            CREATE TABLE unit_procurements (
                id SERIAL PRIMARY KEY,
                unit_id INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending_verification' NOT NULL,
                requested_by INTEGER NOT NULL,
                request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                verified_by INTEGER,
                verification_date TIMESTAMP,
                verification_notes TEXT,
                approved_by INTEGER,
                approval_date TIMESTAMP,
                rejected_by INTEGER,
                rejection_date TIMESTAMP,
                rejection_reason TEXT,
                procurement_id INTEGER,
                unit_received_by INTEGER,
                unit_receipt_date TIMESTAMP,
                request_notes TEXT,
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (requested_by) REFERENCES users(id),
                FOREIGN KEY (verified_by) REFERENCES users(id),
                FOREIGN KEY (approved_by) REFERENCES users(id),
                FOREIGN KEY (rejected_by) REFERENCES users(id),
                FOREIGN KEY (procurement_id) REFERENCES procurements(id),
                FOREIGN KEY (unit_received_by) REFERENCES users(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 2: Create unit_procurement_items table
        print("\n2. Creating unit_procurement_items table...")
        db.session.execute(db.text("""
            CREATE TABLE unit_procurement_items (
                id SERIAL PRIMARY KEY,
                unit_procurement_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity INTEGER NOT NULL,
                new_item_name VARCHAR(200),
                new_item_category_id INTEGER,
                new_item_unit VARCHAR(50),
                linked_procurement_item_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_procurement_id) REFERENCES unit_procurements(id),
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (new_item_category_id) REFERENCES categories(id),
                FOREIGN KEY (linked_procurement_item_id) REFERENCES procurement_items(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 3: Create indexes for better performance
        print("\n3. Creating indexes...")
        db.session.execute(db.text("""
            CREATE INDEX idx_unit_procurements_unit_id ON unit_procurements(unit_id);
        """))
        db.session.commit()
        print("   ✓ Index on unit_procurements.unit_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_unit_procurements_status ON unit_procurements(status);
        """))
        db.session.commit()
        print("   ✓ Index on unit_procurements.status")

        db.session.execute(db.text("""
            CREATE INDEX idx_unit_procurements_requested_by ON unit_procurements(requested_by);
        """))
        db.session.commit()
        print("   ✓ Index on unit_procurements.requested_by")

        db.session.execute(db.text("""
            CREATE INDEX idx_unit_procurement_items_procurement_id ON unit_procurement_items(unit_procurement_id);
        """))
        db.session.commit()
        print("   ✓ Index on unit_procurement_items.unit_procurement_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_unit_procurements_procurement_id ON unit_procurements(procurement_id);
        """))
        db.session.commit()
        print("   ✓ Index on unit_procurements.procurement_id")

        print("\n✓ Migration completed successfully!")
        print("\nTables created:")
        print("- unit_procurements: Header permohonan pengadaan dari unit")
        print("- unit_procurement_items: Detail items dalam permohonan pengadaan unit")
        print("\nIndexes created for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Drop unit_procurements tables...")

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'unit_procurement_items' not in tables and 'unit_procurements' not in tables:
            print("Tables do not exist. Nothing to rollback.")
            return

        # Drop in correct order (child first)
        if 'unit_procurement_items' in tables:
            print("\nDropping unit_procurement_items table...")
            db.session.execute(db.text("DROP TABLE unit_procurement_items;"))
            db.session.commit()
            print("   ✓ Table dropped")

        if 'unit_procurements' in tables:
            print("\nDropping unit_procurements table...")
            db.session.execute(db.text("DROP TABLE unit_procurements;"))
            db.session.commit()
            print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for unit_procurements tables')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
