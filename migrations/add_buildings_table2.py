"""
Migration untuk menambahkan tabel buildings dan relasi ke units
Run: python migrations/add_buildings_table2.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.facilities import Building

def upgrade():
    """Create buildings table and add building_id to units"""
    app = create_app()

    with app.app_context():
        # Create buildings table
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS buildings (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                address TEXT,
                geom GEOMETRY(POINT, 4326),
                zone_geom GEOMETRY(POLYGON, 4326),
                zone_json TEXT,
                floor_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Add building_id column to units
        db.session.execute(db.text("""
            ALTER TABLE units
            ADD COLUMN IF NOT EXISTS building_id INTEGER REFERENCES buildings(id)
        """))

        db.session.commit()
        print("Successfully created buildings table and added building_id to units")

def downgrade():
    """Drop buildings table and remove building_id from units"""
    app = create_app()

    with app.app_context():
        # Remove building_id from units
        db.session.execute(db.text("""
            ALTER TABLE units DROP COLUMN IF EXISTS building_id
        """))

        # Drop buildings table
        db.session.execute(db.text("""
            DROP TABLE IF EXISTS buildings
        """))

        db.session.commit()
        print("Successfully dropped buildings table and removed building_id from units")

if __name__ == '__main__':
    upgrade()
