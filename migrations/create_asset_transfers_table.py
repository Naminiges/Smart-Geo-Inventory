"""
Migration script to create asset_transfers table
This table logs/history all asset transfers between units/rooms
"""
from app import create_app, db
from app.models.asset_transfer import AssetTransfer

def migrate():
    """Create asset_transfers table"""
    app = create_app()

    with app.app_context():
        print("Creating asset_transfers table...")

        # Create the table
        db.create_all()

        # Verify table was created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        if 'asset_transfers' in tables:
            print("✓ Successfully created 'asset_transfers' table")
            print("\nTable structure:")
            columns = inspector.get_columns('asset_transfers')
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        else:
            print("✗ Failed to create 'asset_transfers' table")
            return False

        print("\nMigration completed successfully!")
        return True

if __name__ == '__main__':
    migrate()
