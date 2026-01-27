"""
Migration untuk menghapus kolom unit_id dari tabel unit_details
Karena unit_details sekarang hanya berelasi dengan buildings

Run: python migrations/remove_unit_id_from_unit_details.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== MIGRATION: REMOVE UNIT_ID FROM UNIT_DETAILS ===\n")

    try:
        # Step 1: Pastikan semua unit_details sudah memiliki building_id
        print("Step 1: Checking building_id...")
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM unit_details WHERE building_id IS NULL"
        )).scalar()

        if result > 0:
            print(f"WARNING: Ada {result} unit_details tanpa building_id!")
            print("Migrasi dibatalkan. Silakan set building_id terlebih dahulu.")
            sys.exit(1)
        else:
            print("✓ Semua unit_details sudah memiliki building_id")

        # Step 2: Buat backup data (opsional)
        print("\nStep 2: Creating backup...")
        db.session.execute(text(
            "CREATE TABLE IF NOT EXISTS unit_details_backup AS "
            "SELECT * FROM unit_details"
        ))
        print("✓ Backup created: unit_details_backup")

        # Step 3: Hapus foreign key constraint untuk unit_id
        print("\nStep 3: Dropping foreign key constraint...")
        try:
            db.session.execute(text(
                "ALTER TABLE unit_details "
                "DROP CONSTRAINT IF EXISTS unit_details_unit_id_fkey"
            ))
            print("✓ Foreign key constraint dropped")
        except Exception as e:
            print(f"Info: {str(e)}")

        # Step 4: Hapus kolom unit_id
        print("\nStep 4: Dropping unit_id column...")
        db.session.execute(text(
            "ALTER TABLE unit_details DROP COLUMN IF EXISTS unit_id"
        ))
        print("✓ Column unit_id dropped")

        # Step 5: Buat building_id menjadi NOT NULL
        print("\nStep 5: Making building_id NOT NULL...")
        db.session.execute(text(
            "ALTER TABLE unit_details "
            "ALTER COLUMN building_id SET NOT NULL"
        ))
        print("✓ Column building_id is now NOT NULL")

        # Commit semua perubahan
        db.session.commit()
        print("\n=== MIGRATION SELESAI ===")
        print("✓ unit_details sekarang hanya berelasi dengan buildings")
        print("✓ Kolom unit_id telah dihapus")
        print("✓ Kolom building_id sekarang NOT NULL")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        print("Rollback performed. No changes were made.")
        sys.exit(1)
