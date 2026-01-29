"""
Migration untuk menghapus kolom building_id dari tabel units
Unit sekarang hanya sebagai tenant/departemen tanpa berelasi dengan gedung

Run: python migrations/remove_building_id_from_units.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== MIGRATION: REMOVE BUILDING_ID FROM UNITS ===\n")

    try:
        # Step 1: Buat backup data
        print("Step 1: Creating backup...")
        db.session.execute(text(
            "CREATE TABLE IF NOT EXISTS units_backup AS "
            "SELECT * FROM units"
        ))
        print("✓ Backup created: units_backup")

        # Step 2: Hapus foreign key constraint untuk building_id
        print("\nStep 2: Dropping foreign key constraint...")
        try:
            db.session.execute(text(
                "ALTER TABLE units "
                "DROP CONSTRAINT IF EXISTS units_building_id_fkey"
            ))
            print("✓ Foreign key constraint dropped")
        except Exception as e:
            print(f"Info: {str(e)}")

        # Step 3: Hapus kolom building_id
        print("\nStep 3: Dropping building_id column...")
        db.session.execute(text(
            "ALTER TABLE units DROP COLUMN IF EXISTS building_id"
        ))
        print("✓ Column building_id dropped")

        # Commit semua perubahan
        db.session.commit()
        print("\n=== MIGRATION SELESAI ===")
        print("✓ units sekarang tidak memiliki relasi dengan buildings")
        print("✓ Unit murni sebagai tenant/departemen")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        print("Rollback performed. No changes were made.")
        sys.exit(1)
