"""
Script untuk membersihkan data room_name di tabel unit_details
Menghapus bagian deskripsi tambahan, sehingga hanya menyimpan kode ruangan

Contoh:
- "GD.A 0201 - Ruang Kepala PSI" -> "GD.A 0201"
- "GD.B 0101 - Lab Komputer" -> "GD.B 0101"

Run: python clean_room_names.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.facilities import UnitDetail

app = create_app()

with app.app_context():
    print("=== MEMBERSIHKAN ROOM NAMES ===\n")

    # Get all unit_details
    details = UnitDetail.query.all()

    print(f"Total {len(details)} ruangan ditemukan\n")

    updated_count = 0
    skipped_count = 0

    for detail in details:
        original_name = detail.room_name
        new_name = None

        # Cek apakah ada pemisah "-" atau karakter lain yang menandakan deskripsi
        if ' - ' in original_name:
            # Split berdasarkan " - " dan ambil bagian pertama
            parts = original_name.split(' - ')
            new_name = parts[0].strip()
        elif '-' in original_name:
            # Split berdasarkan "-" dan ambil bagian pertama
            parts = original_name.split('-')
            new_name = parts[0].strip()
        else:
            # Cek apakah ada lebih dari 2 bagian (misal: "GD.A 0201 Ruang Kepala")
            parts = original_name.split()
            if len(parts) > 2:
                # Ambil 2 bagian pertama (kode gedung dan nomor ruangan)
                new_name = f"{parts[0]} {parts[1]}"
            else:
                # Sudah dalam format yang benar
                new_name = original_name

        # Hapus spasi berlebih
        new_name = ' '.join(new_name.split())

        # Update jika ada perubahan
        if new_name != original_name:
            detail.room_name = new_name
            updated_count += 1
            print(f"✓ Updated: ID {detail.id}")
            print(f"  Before: {original_name}")
            print(f"  After:  {new_name}\n")
        else:
            skipped_count += 1

    # Commit perubahan
    if updated_count > 0:
        db.session.commit()
        print(f"\n=== SELESAI ===")
        print(f"Total updated: {updated_count}")
        print(f"Total skipped: {skipped_count}")
    else:
        print("\nTidak ada perubahan yang diperlukan. Semua room_name sudah dalam format yang benar.")
