from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Building, Unit
from app.forms.building_forms import BuildingForm
from app.utils.decorators import admin_required

bp = Blueprint('admin_buildings', __name__, url_prefix='/admin/buildings')


@bp.route('/')
@login_required
@admin_required
def index():
    """Display all buildings"""
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

    return render_template('admin/buildings/index.html', buildings=buildings, building_stats=building_stats)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Create a new building"""
    form = BuildingForm()

    if form.validate_on_submit():
        import json

        building = Building(
            code=form.code.data,
            name=form.name.data,
            address=form.address.data,
            floor_count=form.floor_count.data or 1
        )

        # Save zone data if provided
        if form.zone_coordinates.data:
            zone_coords = json.loads(form.zone_coordinates.data)
            building.zone_json = json.dumps({
                "type": "Feature",
                "properties": {
                    "nama": form.name.data,
                    "kode_zona": form.zone_kode.data,
                    "deskripsi": form.zone_deskripsi.data
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [zone_coords]
                }
            })

        building.save()
        flash(f'Gedung {building.name} berhasil ditambahkan', 'success')
        return redirect(url_for('admin_buildings.index'))

    return render_template('admin/buildings/create.html', form=form)


@bp.route('/<int:building_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(building_id):
    """Edit a building"""
    building = Building.query.get_or_404(building_id)
    form = BuildingForm(obj=building)

    if form.validate_on_submit():
        import json

        building.code = form.code.data
        building.name = form.name.data
        building.address = form.address.data
        building.floor_count = form.floor_count.data or 1

        # Save zone data if provided
        if form.zone_coordinates.data:
            zone_coords = json.loads(form.zone_coordinates.data)
            building.zone_json = json.dumps({
                "type": "Feature",
                "properties": {
                    "nama": form.name.data,
                    "kode_zona": form.zone_kode.data,
                    "deskripsi": form.zone_deskripsi.data
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [zone_coords]
                }
            })

        db.session.commit()
        flash(f'Gedung {building.name} berhasil diperbarui', 'success')
        return redirect(url_for('admin_buildings.index'))

    # Pre-fill zone data if exists
    if building.zone_json:
        import json
        zone_data = json.loads(building.zone_json)
        form.zone_kode.data = zone_data['properties'].get('kode_zona', '')
        form.zone_deskripsi.data = zone_data['properties'].get('deskripsi', '')
        form.zone_coordinates.data = json.dumps(zone_data['geometry']['coordinates'][0])

    return render_template('admin/buildings/edit.html', form=form, building=building)


@bp.route('/<int:building_id>/edit-zone', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_zone(building_id):
    """Edit building zone only"""
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

    return render_template('admin/buildings/edit_zone.html', building=building, zone_data=zone_data)


@bp.route('/<int:building_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(building_id):
    """Delete a building"""
    building = Building.query.get_or_404(building_id)

    # Check if building has units
    unit_count = Unit.query.filter_by(building_id=building_id).count()
    if unit_count > 0:
        return jsonify({
            'success': False,
            'message': f'Tidak dapat menghapus gedung yang memiliki {unit_count} unit. Pindahkan unit terlebih dahulu.'
        })

    building.delete()
    flash(f'Gedung {building.name} berhasil dihapus', 'success')
    return jsonify({'success': True})


@bp.route('/<int:building_id>/units')
@login_required
@admin_required
def units(building_id):
    """Show units in a building"""
    building = Building.query.get_or_404(building_id)
    units = Unit.query.filter_by(building_id=building_id).order_by(Unit.name).all()

    return render_template('admin/buildings/units.html', building=building, units=units)


@bp.route('/<int:building_id>')
@login_required
@admin_required
def detail(building_id):
    """Building detail page"""
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

    return render_template('admin/buildings/detail.html', building=building, units_with_rooms=sorted_units)
