"""
Migration: Make unit_detail_id nullable in distributions table
This migration allows distributions without specific unit detail (room/level)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Make unit_detail_id nullable...")

        # Check if column already allows NULL
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = inspector.get_columns('distributions')
        unit_detail_col = [col for col in columns if col['name'] == 'unit_detail_id'][0]

        if not unit_detail_col['nullable']:
            # Step 1: Alter column to allow NULL
            print("\n1. Altering unit_detail_id to allow NULL...")
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ALTER COLUMN unit_detail_id DROP NOT NULL;
            """))
            db.session.commit()
            print("   ✓ Column unit_detail_id now allows NULL")
        else:
            print("Column unit_detail_id already allows NULL. Skipping migration.")

        print("\n✓ Migration completed successfully!")
        print("\nChanges:")
        print("- unit_detail_id column now allows NULL values")
        print("- Distributions can be created without specific room/level")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Make unit_detail_id NOT NULL...")

        # Update any NULL values to a default or delete them
        print("\n1. Updating NULL unit_detail_id values...")
        db.session.execute(db.text("""
            UPDATE distributions
            SET unit_detail_id = (
                SELECT ud.id FROM unit_details ud
                JOIN units u ON u.id = ud.unit_id
                WHERE u.id = distributions.unit_id
                LIMIT 1
            )
            WHERE unit_detail_id IS NULL;
        """))
        db.session.commit()
        print("   ✓ NULL values updated")

        # Step 2: Alter column to NOT NULL
        print("\n2. Altering unit_detail_id to NOT NULL...")
        db.session.execute(db.text("""
            ALTER TABLE distributions
            ALTER COLUMN unit_detail_id SET NOT NULL;
        """))
        db.session.commit()
        print("   ✓ Column unit_detail_id now requires NOT NULL")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for unit_detail_id nullable')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
