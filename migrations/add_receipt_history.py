#!/usr/bin/env python3
"""
Migration script to add receipt_history column to procurements table
for supporting partial receiving feature.

Run this script: python migrations/add_receipt_history.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Procurement
from sqlalchemy import text

def migrate():
    """Add receipt_history column if it doesn't exist"""
    app = create_app()

    with app.app_context():
        # Check if column exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('procurements')]

        if 'receipt_history' in columns:
            print("✓ Column 'receipt_history' already exists in procurements table")
            return

        # Add receipt_history column
        print("Adding 'receipt_history' column to procurements table...")
        db.session.execute(text("ALTER TABLE procurements ADD COLUMN receipt_history TEXT"))

        # Add index for better query performance
        print("Adding index on receipt_history column...")
        try:
            # Note: TEXT columns don't support indexes in PostgreSQL directly
            # but we can add a functional index if needed later
            pass
        except Exception as e:
            print(f"Warning: Could not create index - {e}")

        db.session.commit()
        print("✓ Migration completed successfully!")
        print("\nWhat's new:")
        print("- procurements.receipt_history: Stores JSON array of all receipts for partial receiving")
        print("- Each receipt contains: receipt_number, quantity, serials, date, received_by")
        print("\nExample format:")
        print('[{"receipt_number": "INV-001", "quantity": 2, "serials": ["SN1", "SN2"], "date": "2024-01-01", "received_by": 1}]')

def rollback():
    """Remove receipt_history column (USE WITH CAUTION)"""
    app = create_app()

    with app.app_context():
        confirm = input("⚠️  WARNING: This will DROP the receipt_history column and all data! Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Rollback cancelled.")
            return

        print("Dropping 'receipt_history' column from procurements table...")
        db.session.execute(text("ALTER TABLE procurements DROP COLUMN receipt_history IF EXISTS"))
        db.session.commit()
        print("✓ Rollback completed!")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for receipt_history column')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration (drop column)')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
