"""
Migration: Add distributed_by and distributed_at to asset_requests
This migration tracks who distributed the asset request and when
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Add distribution tracking to asset_requests...")

        # Check if columns already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('asset_requests')]

        if 'distributed_by' in columns:
            print("Columns already exist. Skipping migration.")
            return

        # Step 1: Add distributed_by column
        print("\n1. Adding distributed_by column...")
        db.session.execute(db.text("""
            ALTER TABLE asset_requests
            ADD COLUMN distributed_by INTEGER REFERENCES users(id);
        """))
        db.session.commit()
        print("   ✓ Column distributed_by added")

        # Step 2: Add distributed_at column
        print("\n2. Adding distributed_at column...")
        db.session.execute(db.text("""
            ALTER TABLE asset_requests
            ADD COLUMN distributed_at TIMESTAMP;
        """))
        db.session.commit()
        print("   ✓ Column distributed_at added")

        print("\n✓ Migration completed successfully!")
        print("\nChanges:")
        print("- Added distributed_by column (references users)")
        print("- Added distributed_at column (timestamp)")
        print("- Distribution tracking now available")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Remove distribution tracking from asset_requests...")

        # Check if columns exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('asset_requests')]

        if 'distributed_by' not in columns and 'distributed_at' not in columns:
            print("Columns do not exist. Nothing to rollback.")
            return

        # Drop columns
        print("\nDropping columns...")
        try:
            db.session.execute(db.text("""
                ALTER TABLE asset_requests
                DROP COLUMN IF EXISTS distributed_by;
            """))
            db.session.commit()
            print("   ✓ Column distributed_by dropped")
        except:
            pass

        try:
            db.session.execute(db.text("""
                ALTER TABLE asset_requests
                DROP COLUMN IF EXISTS distributed_at;
            """))
            db.session.commit()
            print("   ✓ Column distributed_at dropped")
        except:
            pass

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for distribution tracking')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
