"""
Migration script to add draft rejection fields to distributions table
"""

from app import create_app, db
from sqlalchemy import text

def add_draft_rejection_fields():
    app = create_app()
    with app.app_context():
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        columns_to_add = {
            'draft_rejected': 'BOOLEAN DEFAULT FALSE',
            'draft_rejected_by': 'INTEGER REFERENCES users(id)',
            'draft_rejected_at': 'TIMESTAMP'
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

        print("\nMigration completed!")

if __name__ == '__main__':
    add_draft_rejection_fields()
