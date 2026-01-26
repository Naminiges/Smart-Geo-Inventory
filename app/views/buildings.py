from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Building, Unit
from app.utils.decorators import role_required

bp = Blueprint('buildings', __name__, url_prefix='/buildings')


@bp.route('/')
@login_required
def index():
    """Display all buildings - accessible by all roles"""
    from app.models.facilities import UnitDetail
    buildings = Building.query.order_by(Building.code).all()

    # Get stats for each building
    building_stats = {}
    for building in buildings:
        # Units headquartered here (via unit.building_id)
        hq_count = Unit.query.filter_by(building_id=building.id).count()

        # Units that have rooms here (via unit_details.building_id)
        room_details = UnitDetail.query.filter_by(building_id=building.id).all()
        unique_units = set(ud.unit_id for ud in room_details)

        building_stats[building.id] = {
            'hq_count': hq_count,
            'unit_count': len(unique_units),
            'room_count': len(room_details),
            'has_zone': bool(building.zone_json)
        }

    return render_template('buildings/index.html', buildings=buildings, building_stats=building_stats)


@bp.route('/<int:building_id>')
@login_required
def detail(building_id):
    """Building detail page - accessible by all roles"""
    from app.models.facilities import UnitDetail
    building = Building.query.get_or_404(building_id)

    # Get all units that have rooms in this building (via unit_details)
    unit_details = UnitDetail.query.filter_by(building_id=building_id).all()

    # Group by unit and count rooms
    units_with_rooms = {}
    for ud in unit_details:
        if ud.unit_id not in units_with_rooms:
            units_with_rooms[ud.unit_id] = {
                'unit': ud.unit,
                'room_count': 0,
                'rooms': []
            }
        units_with_rooms[ud.unit_id]['room_count'] += 1
        units_with_rooms[ud.unit_id]['rooms'].append(ud)

    # Sort by room count
    sorted_units = sorted(units_with_rooms.values(), key=lambda x: x['room_count'], reverse=True)

    return render_template('buildings/detail.html', building=building, units_with_rooms=sorted_units)


@bp.route('/<int:building_id>/edit-zone', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_zone(building_id):
    """Edit building zone only - admin only"""
    building = Building.query.get_or_404(building_id)

    if request.method == 'POST':
        import json

        data = request.get_json()
        zone_coords = data.get('coordinates', [])

        if zone_coords:
            building.zone_json = json.dumps({
                "type": "Feature",
                "properties": {
                    "nama": building.name,
                    "kode_zona": data.get('kode', ''),
                    "deskripsi": data.get('deskripsi', '')
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [zone_coords]
                }
            })

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Zona {building.name} berhasil diperbarui'
            })

    # Get existing zone data
    zone_data = None
    if building.zone_json:
        import json
        zone_data = json.loads(building.zone_json)

    return render_template('buildings/edit_zone.html', building=building, zone_data=zone_data)
