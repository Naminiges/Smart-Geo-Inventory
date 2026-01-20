"""
Add verification fields to distributions table
This migration adds fields for task type and verification workflow
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add verification columns to distributions table"""
    app = create_app()

    with app.app_context():
        # Check if columns exist before adding
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('distributions')]

        print(f"Current columns: {columns}")

        # Add task_type column
        if 'task_type' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN task_type VARCHAR(50) DEFAULT 'installation'
            """))
            logger.info("Added column: task_type")
            print("[OK] Added column: task_type")
        else:
            print("[SKIP] Column task_type already exists")

        # Add verification_photo column
        if 'verification_photo' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verification_photo VARCHAR(500)
            """))
            logger.info("Added column: verification_photo")
            print("[OK] Added column: verification_photo")
        else:
            print("[SKIP] Column verification_photo already exists")

        # Add verification_notes column
        if 'verification_notes' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verification_notes TEXT
            """))
            logger.info("Added column: verification_notes")
            print("[OK] Added column: verification_notes")
        else:
            print("[SKIP] Column verification_notes already exists")

        # Add verified_by column (foreign key to users)
        if 'verified_by' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verified_by INTEGER
            """))
            logger.info("Added column: verified_by")
            print("[OK] Added column: verified_by")
        else:
            print("[SKIP] Column verified_by already exists")

        # Add verified_at column
        if 'verified_at' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verified_at TIMESTAMP
            """))
            logger.info("Added column: verified_at")
            print("[OK] Added column: verified_at")
        else:
            print("[SKIP] Column verified_at already exists")

        # Add verification_status column
        if 'verification_status' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verification_status VARCHAR(50) DEFAULT 'pending'
            """))
            logger.info("Added column: verification_status")
            print("[OK] Added column: verification_status")
        else:
            print("[SKIP] Column verification_status already exists")

        # Add verification_rejection_reason column
        if 'verification_rejection_reason' not in columns:
            db.session.execute(db.text("""
                ALTER TABLE distributions
                ADD COLUMN verification_rejection_reason TEXT
            """))
            logger.info("Added column: verification_rejection_reason")
            print("[OK] Added column: verification_rejection_reason")
        else:
            print("[SKIP] Column verification_rejection_reason already exists")

        db.session.commit()
        logger.info("Migration completed successfully")
        print("\n[SUCCESS] Migration completed successfully!")


if __name__ == '__main__':
    upgrade()
