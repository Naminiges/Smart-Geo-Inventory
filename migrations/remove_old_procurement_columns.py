"""
Quick Migration: Remove old columns from procurements table
This script removes the old columns that are no longer needed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Remove old columns from procurements table...")

        # List of columns to remove
        columns_to_remove = [
            'item_id',
            'quantity',
            'unit_price',
            'serial_numbers',
            'receipt_history',
            'new_item_name',
            'new_item_category_id',
            'new_item_unit',
            'actual_quantity'
        ]

        for column in columns_to_remove:
            try:
                print(f"\nRemoving column: {column}")
                db.session.execute(db.text(f"""
                    ALTER TABLE procurements DROP COLUMN IF EXISTS {column};
                """))
                db.session.commit()
                print(f"   ✓ Column {column} removed successfully")
            except Exception as e:
                print(f"   ✗ Error removing {column}: {str(e)}")
                db.session.rollback()

        print("\n✓ Migration completed!")
        print("\nColumns removed from procurements table.")
        print("Now procurements table is ready for the new multiple items system.")


if __name__ == '__main__':
    migrate()
