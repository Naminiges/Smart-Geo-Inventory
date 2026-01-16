"""
Migration: Update procurements table to use category_id foreign key instead of category string

This migration:
1. Adds new column new_item_category_id (integer, FK to categories.id)
2. Migrates data from new_item_category (string) to new_item_category_id by matching category names
3. Drops the old new_item_category column
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Category

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Update procurements category column...")

        # Check if new_item_category_id column already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('procurements')]

        if 'new_item_category_id' in columns:
            print("Column new_item_category_id already exists. Skipping migration.")
            return

        # Step 1: Add the new column
        print("\n1. Adding new_item_category_id column...")
        db.session.execute(db.text("""
            ALTER TABLE procurements
            ADD COLUMN new_item_category_id INTEGER;
        """))
        db.session.commit()
        print("   ✓ Column added successfully")

        # Step 2: Migrate data from string to foreign key
        print("\n2. Migrating data from new_item_category to new_item_category_id...")

        # Get all categories
        categories = Category.query.all()
        category_name_to_id = {cat.name.lower(): cat.id for cat in categories}

        # Get procurements with new_item_category values
        result = db.session.execute(db.text("""
            SELECT id, new_item_category
            FROM procurements
            WHERE new_item_category IS NOT NULL
            AND new_item_category != ''
        """))

        rows = result.fetchall()
        migrated_count = 0
        not_found_categories = set()

        for row in rows:
            procurement_id = row[0]
            category_name = row[1]

            # Try to find matching category ID
            category_id = category_name_to_id.get(category_name.lower())

            if category_id:
                db.session.execute(db.text("""
                    UPDATE procurements
                    SET new_item_category_id = :category_id
                    WHERE id = :procurement_id
                """), {'category_id': category_id, 'procurement_id': procurement_id})
                migrated_count += 1
            else:
                not_found_categories.add(category_name)

        db.session.commit()
        print(f"   ✓ Migrated {migrated_count} procurements")

        if not_found_categories:
            print(f"   ! Warning: {len(not_found_categories)} procurements had categories that don't exist in the categories table:")
            for cat_name in list(not_found_categories)[:5]:
                print(f"     - {cat_name}")
            if len(not_found_categories) > 5:
                print(f"     ... and {len(not_found_categories) - 5} more")

        # Step 3: Drop the old column
        print("\n3. Dropping old new_item_category column...")
        db.session.execute(db.text("""
            ALTER TABLE procurements
            DROP COLUMN new_item_category;
        """))
        db.session.commit()
        print("   ✓ Old column dropped successfully")

        # Step 4: Add foreign key constraint
        print("\n4. Adding foreign key constraint...")
        db.session.execute(db.text("""
            ALTER TABLE procurements
            ADD CONSTRAINT fk_procurements_new_item_category_id
            FOREIGN KEY (new_item_category_id) REFERENCES categories(id);
        """))
        db.session.commit()
        print("   ✓ Foreign key constraint added")

        print("\n✓ Migration completed successfully!")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Restore procurements category column...")

        # Check if new_item_category column exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('procurements')]

        if 'new_item_category' in columns:
            print("Column new_item_category still exists. Nothing to rollback.")
            return

        # Step 1: Drop foreign key constraint
        print("\n1. Dropping foreign key constraint...")
        try:
            db.session.execute(db.text("""
                ALTER TABLE procurements
                DROP CONSTRAINT IF EXISTS fk_procurements_new_item_category_id;
            """))
            db.session.commit()
            print("   ✓ Foreign key constraint dropped")
        except Exception as e:
            print(f"   ! Warning: {str(e)}")

        # Step 2: Drop new_item_category_id column
        print("\n2. Dropping new_item_category_id column...")
        db.session.execute(db.text("""
            ALTER TABLE procurements
            DROP COLUMN IF EXISTS new_item_category_id;
        """))
        db.session.commit()
        print("   ✓ Column dropped")

        # Step 3: Add back the old column
        print("\n3. Restoring new_item_category column...")
        db.session.execute(db.text("""
            ALTER TABLE procurements
            ADD COLUMN new_item_category VARCHAR(100);
        """))
        db.session.commit()
        print("   ✓ Old column restored")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for procurements category column')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
