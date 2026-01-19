"""
Migration: Add procurement_items table for multiple items in procurement

This migration:
1. Creates procurement_items table
2. Migrates existing data from procurements table to procurement_items
3. Removes item_id, quantity, unit_price columns from procurements table
4. Moves serial_numbers, receipt_history, new_item_* columns to procurement_items
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add procurement_items table...")

        # Check if procurement_items table already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'procurement_items' in tables:
            print("Table procurement_items already exists. Skipping migration.")
            return

        # Step 1: Create procurement_items table
        print("\n1. Creating procurement_items table...")
        db.session.execute(db.text("""
            CREATE TABLE procurement_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procurement_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity INTEGER NOT NULL,
                serial_numbers TEXT,
                actual_quantity INTEGER DEFAULT 0,
                receipt_history TEXT,
                new_item_name VARCHAR(200),
                new_item_category_id INTEGER,
                new_item_unit VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (procurement_id) REFERENCES procurements(id),
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (new_item_category_id) REFERENCES categories(id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Step 2: Migrate existing data from procurements to procurement_items
        print("\n2. Migrating existing procurement data...")

        # Get all procurements with item_id
        result = db.session.execute(db.text("""
            SELECT id, item_id, quantity, unit_price, serial_numbers,
                   actual_quantity, receipt_history, new_item_name,
                   new_item_category_id, new_item_unit
            FROM procurements
            WHERE item_id IS NOT NULL
        """))

        rows = result.fetchall()
        migrated_count = 0

        for row in rows:
            procurement_id = row[0]
            item_id = row[1]
            quantity = row[2]
            serial_numbers = row[4]
            actual_quantity = row[5]
            receipt_history = row[6]
            new_item_name = row[7]
            new_item_category_id = row[8]
            new_item_unit = row[9]

            # Insert into procurement_items
            db.session.execute(db.text("""
                INSERT INTO procurement_items (
                    procurement_id, item_id, quantity, serial_numbers,
                    actual_quantity, receipt_history, new_item_name,
                    new_item_category_id, new_item_unit
                )
                VALUES (
                    :procurement_id, :item_id, :quantity, :serial_numbers,
                    :actual_quantity, :receipt_history, :new_item_name,
                    :new_item_category_id, :new_item_unit
                )
            """), {
                'procurement_id': procurement_id,
                'item_id': item_id,
                'quantity': quantity,
                'serial_numbers': serial_numbers,
                'actual_quantity': actual_quantity or 0,
                'receipt_history': receipt_history,
                'new_item_name': new_item_name,
                'new_item_category_id': new_item_category_id,
                'new_item_unit': new_item_unit
            })
            migrated_count += 1

        db.session.commit()
        print(f"   ✓ Migrated {migrated_count} procurements to procurement_items")

        # Step 3: Drop columns from procurements table
        print("\n3. Removing old columns from procurements table...")

        columns_to_drop = [
            'item_id',
            'quantity',
            'unit_price',
            'serial_numbers',
            'receipt_history',
            'new_item_name',
            'new_item_category_id',
            'new_item_unit'
        ]

        for column in columns_to_drop:
            try:
                db.session.execute(db.text(f"""
                    ALTER TABLE procurements DROP COLUMN {column};
                """))
                print(f"   ✓ Dropped column {column}")
            except Exception as e:
                print(f"   ! Warning: Could not drop column {column}: {str(e)}")

        db.session.commit()

        print("\n✓ Migration completed successfully!")
        print("\nIMPORTANT NOTES:")
        print("- procurement_items table created")
        print("- Existing data migrated from procurements table")
        print("- Old columns removed from procurements table")
        print("- Each procurement can now have multiple items")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Remove procurement_items table...")

        # Check if procurement_items table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'procurement_items' not in tables:
            print("Table procurement_items does not exist. Nothing to rollback.")
            return

        # Step 1: Add back columns to procurements table
        print("\n1. Restoring columns to procurements table...")

        columns_to_add = [
            ("item_id", "INTEGER"),
            ("quantity", "INTEGER NOT NULL DEFAULT 1"),
            ("unit_price", "FLOAT"),
            ("serial_numbers", "TEXT"),
            ("receipt_history", "TEXT"),
            ("new_item_name", "VARCHAR(200)"),
            ("new_item_category_id", "INTEGER"),
            ("new_item_unit", "VARCHAR(50)")
        ]

        for column, col_type in columns_to_add:
            try:
                db.session.execute(db.text(f"""
                    ALTER TABLE procurements ADD COLUMN {column} {col_type};
                """))
                print(f"   ✓ Added column {column}")
            except Exception as e:
                print(f"   ! Warning: Could not add column {column}: {str(e)}")

        db.session.commit()

        # Step 2: Migrate data back from procurement_items to procurements
        print("\n2. Migrating data back to procurements table...")

        # Get first procurement_item for each procurement
        result = db.session.execute(db.text("""
            SELECT procurement_id, item_id, quantity, serial_numbers,
                   actual_quantity, receipt_history, new_item_name,
                   new_item_category_id, new_item_unit
            FROM procurement_items
            GROUP BY procurement_id
        """))

        rows = result.fetchall()
        migrated_count = 0

        for row in rows:
            procurement_id = row[0]
            item_id = row[1]
            quantity = row[2]
            serial_numbers = row[3]
            actual_quantity = row[4]
            receipt_history = row[5]
            new_item_name = row[6]
            new_item_category_id = row[7]
            new_item_unit = row[8]

            # Update procurements table
            db.session.execute(db.text("""
                UPDATE procurements
                SET item_id = :item_id,
                    quantity = :quantity,
                    serial_numbers = :serial_numbers,
                    actual_quantity = :actual_quantity,
                    receipt_history = :receipt_history,
                    new_item_name = :new_item_name,
                    new_item_category_id = :new_item_category_id,
                    new_item_unit = :new_item_unit
                WHERE id = :procurement_id
            """), {
                'procurement_id': procurement_id,
                'item_id': item_id,
                'quantity': quantity,
                'serial_numbers': serial_numbers,
                'actual_quantity': actual_quantity,
                'receipt_history': receipt_history,
                'new_item_name': new_item_name,
                'new_item_category_id': new_item_category_id,
                'new_item_unit': new_item_unit
            })
            migrated_count += 1

        db.session.commit()
        print(f"   ✓ Migrated {migrated_count} procurements")

        # Step 3: Add foreign key constraints
        print("\n3. Adding foreign key constraints...")

        try:
            db.session.execute(db.text("""
                ALTER TABLE procurements
                ADD CONSTRAINT fk_procurements_item_id
                FOREIGN KEY (item_id) REFERENCES items(id);
            """))
            print("   ✓ Added FK for item_id")
        except Exception as e:
            print(f"   ! Warning: Could not add FK for item_id: {str(e)}")

        try:
            db.session.execute(db.text("""
                ALTER TABLE procurements
                ADD CONSTRAINT fk_procurements_new_item_category_id
                FOREIGN KEY (new_item_category_id) REFERENCES categories(id);
            """))
            print("   ✓ Added FK for new_item_category_id")
        except Exception as e:
            print(f"   ! Warning: Could not add FK for new_item_category_id: {str(e)}")

        db.session.commit()

        # Step 4: Drop procurement_items table
        print("\n4. Dropping procurement_items table...")
        db.session.execute(db.text("""
            DROP TABLE procurement_items;
        """))
        db.session.commit()
        print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for procurement_items table')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
