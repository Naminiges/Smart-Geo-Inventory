"""
Migration script to add draft fields to distributions table
"""

from app import create_app, db
from sqlalchemy import text

def add_draft_fields():
    app = create_app()
    with app.app_context():
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        columns_to_add = {
            'is_draft': 'BOOLEAN DEFAULT FALSE',
            'draft_created_by': 'INTEGER REFERENCES users(id)',
            'draft_notes': 'TEXT',
            'draft_verified_by': 'INTEGER REFERENCES users(id)',
            'draft_verified_at': 'TIMESTAMP',
            'draft_rejection_reason': 'TEXT'
        }

        for col_name, col_type in columns_to_add.items():
            if col_name not in columns:
                print(f"Adding column: {col_name}")
                with db.engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE distributions ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                print(f"  Successfully added {col_name}")
            else:
                print(f"Column {col_name} already exists, skipping...")

        # Make field_staff_id nullable if it's NOT NULL
        field_staff_column = [col for col in inspector.get_columns('distributions') if col['name'] == 'field_staff_id'][0]
        if field_staff_column and not field_staff_column['nullable']:
            print("Making field_staff_id nullable...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE distributions ALTER COLUMN field_staff_id DROP NOT NULL"))
                conn.commit()
            print("  Successfully made field_staff_id nullable")

        print("\nMigration completed!")

if __name__ == '__main__':
    add_draft_fields()
