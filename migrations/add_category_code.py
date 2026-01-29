"""
Add category code column

This migration adds a 'code' column to the categories table
to store category codes used as prefixes for item codes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Category
from sqlalchemy import text

def upgrade():
    """Add code column to categories table and update existing categories"""
    app = create_app()

    with app.app_context():
        # Check if column already exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('categories')]

        if 'code' not in columns:
            # Add the code column as nullable first
            db.session.execute(text("""
                ALTER TABLE categories
                ADD COLUMN code VARCHAR(10)
            """))
            db.session.commit()

            print("✅ Column code added to categories table")

            # Update existing categories with appropriate codes
            categories = Category.query.all()

            category_codes = {
                'Jaringan': 'JAR',
                'Elektronik': 'ELE',
                'Server': 'SRV',
                'Lainnya': 'LNY',
                'Mebel': 'MEB'
            }

            for category in categories:
                if category.name in category_codes:
                    category.code = category_codes[category.name]
                else:
                    # Generate code from name if not in predefined list
                    code = category.name[:3].upper()
                    # Ensure uniqueness
                    counter = 1
                    original_code = code
                    while Category.query.filter_by(code=code).first():
                        code = f"{original_code}{counter}"
                        counter += 1
                    category.code = code

            db.session.commit()

            # Now make the column NOT NULL and UNIQUE
            db.session.execute(text("""
                ALTER TABLE categories
                ALTER COLUMN code SET NOT NULL
            """))
            db.session.execute(text("""
                ALTER TABLE categories
                ADD CONSTRAINT categories_code_key UNIQUE (code)
            """))
            db.session.commit()

            print("✅ Existing categories updated with codes")
            print("✅ Column code is now NOT NULL and UNIQUE")
        else:
            print("⚠️  Column code already exists in categories table")

def downgrade():
    """Remove code column from categories table"""
    app = create_app()

    with app.app_context():
        db.session.execute(text("""
            ALTER TABLE categories
            DROP COLUMN IF EXISTS code
        """))
        db.session.commit()

        print("✅ Column code removed from categories table")

if __name__ == '__main__':
    upgrade()

