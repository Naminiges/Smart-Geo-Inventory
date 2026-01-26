"""
Add asset_request_id and asset_request_item_id columns to distributions table
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add asset request link columns to distributions table"""
    app = create_app()

    with app.app_context():
        # Check if columns exist before adding
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        print(f"Current columns: {columns}")

        # Add asset_request_id column
        if 'asset_request_id' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN asset_request_id INTEGER,
                ADD CONSTRAINT fk_distributions_asset_request
                FOREIGN KEY (asset_request_id) REFERENCES asset_requests(id)
            """))
            logger.info("Added column: asset_request_id")
            print("[OK] Added column: asset_request_id")
        else:
            print("[SKIP] Column asset_request_id already exists")

        # Add asset_request_item_id column
        if 'asset_request_item_id' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN asset_request_item_id INTEGER,
                ADD CONSTRAINT fk_distributions_asset_request_item
                FOREIGN KEY (asset_request_item_id) REFERENCES asset_request_items(id)
            """))
            logger.info("Added column: asset_request_item_id")
            print("[OK] Added column: asset_request_item_id")
        else:
            print("[SKIP] Column asset_request_item_id already exists")

        db.session.commit()
        print("\n[SUCCESS] Migration completed successfully!")


if __name__ == '__main__':
    upgrade()
