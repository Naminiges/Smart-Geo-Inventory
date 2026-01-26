"""
Migration: Add serial_unit column to item_details table
"""

def upgrade():
    from app import create_app, db
    from app.models.master_data import ItemDetail

    app = create_app()
    with app.app_context():
        # Check if column exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('item_details')]

        if 'serial_unit' not in columns:
            # Add serial_unit column
            db.engine.execute('ALTER TABLE item_details ADD COLUMN serial_unit VARCHAR(100)')
            print("Column 'serial_unit' added to item_details table")
        else:
            print("Column 'serial_unit' already exists in item_details table")

def downgrade():
    from app import create_app, db
    from app.models.master_data import ItemDetail

    app = create_app()
    with app.app_context():
        # Drop serial_unit column
        db.engine.execute('ALTER TABLE item_details DROP COLUMN serial_unit')
        print("Column 'serial_unit' dropped from item_details table")

if __name__ == '__main__':
    upgrade()
