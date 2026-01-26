"""
Migration: Create user_units table
This migration creates table for unit staff assignment to units
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Create user_units table...")

        # Check if table already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'user_units' in tables:
            print("Table user_units already exists. Skipping migration.")
            return

        # Create user_units table
        print("\nCreating user_units table...")
        db.session.execute(db.text("""
            CREATE TABLE user_units (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (unit_id) REFERENCES units(id),
                FOREIGN KEY (assigned_by) REFERENCES users(id),
                UNIQUE (user_id, unit_id)
            );
        """))
        db.session.commit()
        print("   ✓ Table created successfully")

        # Create indexes for better performance
        print("\nCreating indexes...")
        db.session.execute(db.text("""
            CREATE INDEX idx_user_units_user_id ON user_units(user_id);
        """))
        db.session.commit()
        print("   ✓ Index on user_units.user_id")

        db.session.execute(db.text("""
            CREATE INDEX idx_user_units_unit_id ON user_units(unit_id);
        """))
        db.session.commit()
        print("   ✓ Index on user_units.unit_id")

        print("\n✓ Migration completed successfully!")
        print("\nTable created:")
        print("- user_units: Assignment of unit staff to units")


def rollback():
    """Rollback the migration"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Drop user_units table...")

        # Check if table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if 'user_units' not in tables:
            print("Table does not exist. Nothing to rollback.")
            return

        # Drop table
        print("\nDropping user_units table...")
        db.session.execute(db.text("DROP TABLE user_units;"))
        db.session.commit()
        print("   ✓ Table dropped")

        print("\n✓ Rollback completed!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for user_units table')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
