"""
Migrasi data untuk membuat gedung dari unit_details dan hubungkan ke units
Run: python migrate_to_buildings.py
"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.facilities import Building, Unit, UnitDetail

app = create_app()

with app.app_context():
    print("=== MIGRASI DATA KE GEDUNG ===\n")

    # Mapping gedung dari kode ruangan
    gedung_info = {
        'GD.A': {'name': 'Gedung A', 'address': 'Gedung A Lt 2-5, USU', 'floors': 5},
        'GD.B': {'name': 'Gedung B', 'address': 'Gedung B Lt 1, USU', 'floors': 1},
        'GD.C': {'name': 'Gedung C', 'address': 'Gedung C Lt 1, USU', 'floors': 1},
        'GD.D': {'name': 'Gedung D', 'address': 'Gedung D Lt 1, USU', 'floors': 1},
        'GD.E': {'name': 'Gedung E', 'address': 'Gedung E Lt 1, USU', 'floors': 1},
        'GD.F': {'name': 'Gedung F', 'address': 'Gedung F Lt 1, USU', 'floors': 1},
        'GD.G': {'name': 'Gedung G', 'address': 'Gedung G Lt 1, USU', 'floors': 1},
        'GD.H': {'name': 'Gedung H', 'address': 'Gedung H Lt 1, USU', 'floors': 1},
    }

    # Get all unique building codes from unit_details
    details = UnitDetail.query.all()
    building_codes_found = set()
    for detail in details:
        parts = detail.room_name.split()
        if parts:
            code = parts[0]
            if code.startswith('GD.'):
                building_codes_found.add(code)

    print(f"Gedung yang ditemukan: {sorted(building_codes_found)}\n")

    # Create buildings
    buildings_map = {}
    for code in sorted(building_codes_found):
        if code in gedung_info:
            info = gedung_info[code]

            # Check if building already exists
            existing = Building.query.filter_by(code=code).first()
            if existing:
                print(f"Gedung {code} sudah ada: {existing.name}")
                buildings_map[code] = existing
            else:
                building = Building(
                    code=code,
                    name=info['name'],
                    address=info['address'],
                    floor_count=info['floors']
                )
                building.save()
                buildings_map[code] = building
                print(f"Created: {code} - {info['name']}")

    print("\n--- Menghubungkan Units ke Buildings ---\n")

    # Update units dengan building_id berdasarkan unit_details
    units = Unit.query.all()
    for unit in units:
        # Get all unit_details for this unit
        details = UnitDetail.query.filter_by(unit_id=unit.id).all()

        if not details:
            print(f"Unit {unit.id} ({unit.name}): Tidak ada ruangan")
            continue

        # Find all buildings for this unit
        buildings_for_unit = set()
        for detail in details:
            parts = detail.room_name.split()
            if parts and parts[0] in buildings_map:
                buildings_for_unit.add(buildings_map[parts[0]])

        if buildings_for_unit:
            # Jika unit ada di 1 gedung, assign langsung
            if len(buildings_for_unit) == 1:
                building = list(buildings_for_unit)[0]
                unit.building_id = building.id
                print(f"Unit {unit.id} ({unit.name}) -> {building.code} ({building.name})")
            else:
                # Jika unit ada di beberapa gedung, pilih yang paling banyak ruangan
                building_counts = {}
                for detail in details:
                    parts = detail.room_name.split()
                    if parts and parts[0] in buildings_map:
                        b = buildings_map[parts[0]]
                        building_counts[b] = building_counts.get(b, 0) + 1

                if building_counts:
                    main_building = max(building_counts, key=building_counts.get)
                    unit.building_id = main_building.id
                    print(f"Unit {unit.id} ({unit.name}) -> {main_building.code} ({main_building.name}) [main building]")

    db.session.commit()
    print("\n=== MIGRASI SELESAI ===")
