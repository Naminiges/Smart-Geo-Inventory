"""
Migration untuk menambahkan building_id ke unit_details
Run: python migrations/add_building_to_unit_details.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.facilities import Building, UnitDetail

def upgrade():
    """Add building_id column to unit_details and migrate data"""
    app = create_app()

    with app.app_context():
        # Add building_id column to unit_details
        db.session.execute(db.text("""
            ALTER TABLE unit_details
            ADD COLUMN IF NOT EXISTS building_id INTEGER REFERENCES buildings(id)
        """))

        db.session.commit()
        print("Successfully added building_id column to unit_details")

        # Migrate data: parse building code from room_name
        details = UnitDetail.query.all()
        buildings_map = {}

        # Get all buildings
        buildings = Building.query.all()
        for b in buildings:
            buildings_map[b.code] = b.id

        print("\n=== MIGRATING DATA ===")
        updated_count = 0
        for detail in details:
            if detail.room_name:
                parts = detail.room_name.split()
                if parts and parts[0].startswith('GD.'):
                    building_code = parts[0]
                    if building_code in buildings_map:
                        detail.building_id = buildings_map[building_code]
                        updated_count += 1
                        if updated_count <= 10:  # Show first 10
                            print(f"  {detail.room_name} -> {building_code}")

        db.session.commit()
        print(f"\nUpdated {updated_count} unit_details with building_id")
        print("Migration completed successfully")

def downgrade():
    """Remove building_id from unit_details"""
    app = create_app()

    with app.app_context():
        # Remove building_id from unit_details
        db.session.execute(db.text("""
            ALTER TABLE unit_details DROP COLUMN IF EXISTS building_id
        """))

        db.session.commit()
        print("Successfully removed building_id from unit_details")

if __name__ == '__main__':
    upgrade()
