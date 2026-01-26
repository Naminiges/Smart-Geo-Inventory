"""
Add zone geometry columns to units table - Direct SQL version
Run: python migrations/add_unit_zone_columns_direct.py
"""
from app import create_app, db

def upgrade():
    """Add zone_geom and zone_json columns to units table"""
    app = create_app()

    with app.app_context():
        # Add zone_geom column (POLYGON geometry)
        db.session.execute(db.text("""
            ALTER TABLE units
            ADD COLUMN IF NOT EXISTS zone_geom GEOMETRY(POLYGON, 4326)
        """))

        # Add zone_json column (TEXT for storing complete GeoJSON)
        db.session.execute(db.text("""
            ALTER TABLE units
            ADD COLUMN IF NOT EXISTS zone_json TEXT
        """))

        db.session.commit()
        print("Successfully added zone_geom and zone_json columns to units table")

def downgrade():
    """Remove zone_geom and zone_json columns from units table"""
    app = create_app()

    with app.app_context():
        db.session.execute(db.text("""
            ALTER TABLE units DROP COLUMN IF EXISTS zone_geom
        """))
        db.session.execute(db.text("""
            ALTER TABLE units DROP COLUMN IF EXISTS zone_json
        """))
        db.session.commit()
        print("Successfully removed zone_geom and zone_json columns from units table")

if __name__ == '__main__':
    upgrade()
