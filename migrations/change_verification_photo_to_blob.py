"""
Migration script to change verification_photo column type from VARCHAR to BYTEA (BLOB)
in distributions table
Run this script: python migrations/change_verification_photo_to_blob.py
"""

from app import create_app, db
from sqlalchemy import text

def change_verification_photo_to_blob():
    app = create_app()
    with app.app_context():
        # Check current column type
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('distributions')

        verification_photo_col = None
        for col in columns:
            if col['name'] == 'verification_photo':
                verification_photo_col = col
                break

        if not verification_photo_col:
            print("Column 'verification_photo' does not exist in distributions table")
            return

        print(f"Current type: {verification_photo_col['type']}")

        # Check if already BYTEA
        if 'BYTEA' in str(verification_photo_col['type']).upper():
            print("Column 'verification_photo' is already BYTEA type")
            return

        # Change column type to BYTEA
        print("Changing verification_photo column type to BYTEA...")
        with db.engine.connect() as conn:
            # First drop any existing data (converting VARCHAR to BYTEA directly may fail)
            conn.execute(text("UPDATE distributions SET verification_photo = NULL"))

            # Alter column type
            conn.execute(text("ALTER TABLE distributions ALTER COLUMN verification_photo TYPE BYTEA"))
            conn.commit()

        print("Successfully changed 'verification_photo' column type to BYTEA")

if __name__ == '__main__':
    change_verification_photo_to_blob()
