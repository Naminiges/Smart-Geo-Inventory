"""
Sinkronisasi alamat unit berdasarkan unit_details
Parse kode ruangan untuk menentukan gedung, lalu update alamat unit
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models import Unit, UnitDetail

app = create_app()

with app.app_context():
    # Mapping gedung dari kode ruangan
    gedung_map = {
        'GD.A': 'Gedung A Lt 2-5, USU',
        'GD.B': 'Gedung B Lt 1, USU',
        'GD.C': 'Gedung C Lt 1, USU',
        'GD.D': 'Gedung D Lt 1, USU',
        'GD.E': 'Gedung E Lt 1, USU',
        'GD.F': 'Gedung F Lt 1, USU',
        'GD.G': 'Gedung G Lt 1, USU',
        'GD.H': 'Gedung H Lt 1, USU',
    }

    print("=== SINKRONISASI ALAMAT UNIT ===\n")

    # Ambil semua unit
    units = Unit.query.all()

    for unit in units:
        # Ambil semua unit_details untuk unit ini
        details = UnitDetail.query.filter_by(unit_id=unit.id).all()

        if not details:
            print(f"Unit {unit.id} ({unit.name}): Tidak ada ruangan")
            continue

        # Cek gedung dari masing-masing ruangan
        gedung_found = {}
        for detail in details:
            room_name = detail.room_name
            # Extract kode gedung (contoh: "GD.B 0101" -> "GD.B")
            parts = room_name.split()
            if parts:
                kode_gedung = parts[0]
                if kode_gedung not in gedung_found:
                    gedung_found[kode_gedung] = []
                gedung_found[kode_gedung].append(room_name)

        if gedung_found:
            # Tentukan gedung utama (paling banyak ruangan)
            main_gedung = max(gedung_found.keys(), key=lambda k: len(gedung_found[k]))
            new_address = gedung_map.get(main_gedung, f'Gedung {main_gedung}, USU')

            print(f"\nUnit {unit.id}: {unit.name}")
            print(f"  Ruangan di gedung: {list(gedung_found.keys())}")
            print(f"  Gedung utama: {main_gedung}")
            print(f"  Alamat lama: {unit.address}")
            print(f"  Alamat baru: {new_address}")

            # Update alamat unit
            unit.address = new_address

            # Jika semua ruangan di gedung yang sama, gunakan alamat itu
            # Jika campuran, bisa buat alamat gabungan
            if len(gedung_found) > 1:
                gedung_list = sorted(gedung_found.keys())
                gedung_names = []
                for g in gedung_list:
                    if g in gedung_map:
                        gedung_names.append(gedung_map[g].split(',')[0])

                if gedung_names:
                    new_address = ', '.join(gedung_names) + ', USU'
                    print(f"  Alamat gabungan: {new_address}")
                    unit.address = new_address

    # Commit perubahan
    db.session.commit()
    print("\n=== SINKRONISASI SELESAI ===")
    print("Alamat unit telah diperbarui sesuai dengan gedung dari ruangan-ruangannya")
