"""
Migration: Create return_batches and return_items tables
This migration creates tables for tracking returns of items from units back to warehouse
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Create return_batches tables...")

        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'return_batches' in tables:
            print("Table return_batches already exists. Skipping migration.")
            return

        # Step 1: Create return_batches table
        print("\n1. Creating return_batches table...")
        db.session.execute(db.text("""
            CREATE TABLE return_batches (
                id SERIAL PRIMARY KEY,
                batch_code VARCHAR(50) UNIQUE NOT NULL,
                warehouse_id INTEGER NOT NULL,
                return_date DATE NOT NULL,
                notes TEXT,
                status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                created_by INTEGER NOT NULL,
                confirmed_by INTEGER,
                confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (confirmed_by) REFERENCES users(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 2: Create return_items table
        print("\n2. Creating return_items table...")
        db.session.execute(db.text("""
            CREATE TABLE return_items (
                id SERIAL PRIMARY KEY,
                return_batch_id INTEGER NOT NULL,
                item_detail_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                distribution_id INTEGER,
                return_reason TEXT,
                status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                notes TEXT,
                condition VARCHAR(50),
                condition_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (return_batch_id) REFERENCES return_batches(id) ON DELETE CASCADE,
                FOREIGN KEY (item_detail_id) REFERENCES item_details(id),
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (distribution_id) REFERENCES distributions(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 3: Create indexes for better performance
        print("\n3. Creating indexes...")

        # Indexes for return_batches
        db.session.execute(db.text("""
            CREATE INDEX idx_return_batches_batch_code ON return_batches(batch_code);
        """))
        db.session.commit()
        print("   ✓ Index on return_batches.batch_code")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_batches_warehouse_id ON return_batches(warehouse_id);
        """))
        db.session.commit()
        print("   ✓ Index on return_batches.warehouse_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_batches_status ON return_batches(status);
        """))
        db.session.commit()
        print("   ✓ Index on return_batches.status")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_batches_created_by ON return_batches(created_by);
        """))
        db.session.commit()
        print("   ✓ Index on return_batches.created_by")

        # Indexes for return_items
        db.session.execute(db.text("""
            CREATE INDEX idx_return_items_batch_id ON return_items(return_batch_id);
        """))
        db.session.commit()
        print("   ✓ Index on return_items.return_batch_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_items_item_detail_id ON return_items(item_detail_id);
        """))
        db.session.commit()
        print("   ✓ Index on return_items.item_detail_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_items_unit_id ON return_items(unit_id);
        """))
        db.session.commit()
        print("   ✓ Index on return_items.unit_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_items_distribution_id ON return_items(distribution_id);
        """))
        db.session.commit()
        print("   ✓ Index on return_items.distribution_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_return_items_status ON return_items(status);
        """))
        db.session.commit()
        print("   ✓ Index on return_items.status")

        print("\n✓ Migration completed successfully!")
        print("\nTables created:")
        print("- return_batches: Header batch retur barang dari unit ke warehouse")
        print("- return_items: Detail items dalam batch retur")
        print("\nIndexes created for better performance")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Drop return_batches tables...")

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'return_items' not in tables and 'return_batches' not in tables:
            print("Tables do not exist. Nothing to rollback.")
            return

        # Drop in correct order (child first)
        if 'return_items' in tables:
            print("\nDropping return_items table...")
            db.session.execute(db.text("DROP TABLE return_items;"))
            db.session.commit()
            print("   ✓ Table dropped")

        if 'return_batches' in tables:
            print("\nDropping return_batches table...")
            db.session.execute(db.text("DROP TABLE return_batches;"))
            db.session.commit()
            print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for return_batches tables')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
