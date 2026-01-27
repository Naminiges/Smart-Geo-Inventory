"""
Drop supplier-related tables and columns

This migration removes:
1. suppliers table
2. supplier_id column from item_details table
3. supplier_id column from procurements table
"""

from app import create_app, db
from flask_migrate import upgrade
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Drop supplier_id columns and suppliers table"""
    app = create_app()

    with app.app_context():
        # Drop supplier_id column from item_details
        try:
            db.engine.execute(db.text('ALTER TABLE item_details DROP COLUMN IF EXISTS supplier_id'))
            logger.info("Dropped supplier_id column from item_details table")
        except Exception as e:
            logger.warning(f"Could not drop supplier_id from item_details: {e}")

        # Drop supplier_id column from procurements
        try:
            db.engine.execute(db.text('ALTER TABLE procurements DROP COLUMN IF EXISTS supplier_id'))
            logger.info("Dropped supplier_id column from procurements table")
        except Exception as e:
            logger.warning(f"Could not drop supplier_id from procurements: {e}")

        # Drop suppliers table
        try:
            db.engine.execute(db.text('DROP TABLE IF EXISTS suppliers CASCADE'))
            logger.info("Dropped suppliers table")
        except Exception as e:
            logger.warning(f"Could not drop suppliers table: {e}")

        db.session.commit()
        logger.info("Migration completed successfully")


def downgrade():
    """Restore supplier-related tables and columns"""
    app = create_app()

    with app.app_context():
        # Recreate suppliers table
        try:
            db.engine.execute(db.text('''
                CREATE TABLE IF NOT EXISTS suppliers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    contact_person VARCHAR(100),
                    phone VARCHAR(20),
                    email VARCHAR(120),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            logger.info("Recreated suppliers table")
        except Exception as e:
            logger.warning(f"Could not recreate suppliers table: {e}")

        # Add supplier_id column to item_details
        try:
            db.engine.execute(db.text('ALTER TABLE item_details ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id)'))
            logger.info("Added supplier_id column to item_details table")
        except Exception as e:
            logger.warning(f"Could not add supplier_id to item_details: {e}")

        # Add supplier_id column to procurements
        try:
            db.engine.execute(db.text('ALTER TABLE procurements ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id)'))
            logger.info("Added supplier_id column to procurements table")
        except Exception as e:
            logger.warning(f"Could not add supplier_id to procurements: {e}")

        db.session.commit()
        logger.info("Downgrade completed successfully")


if __name__ == '__main__':
    upgrade()
