from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Building
from app.utils.decorators import role_required
from app.forms.warehouse_forms import BuildingForm, UnitDetailForm

bp = Blueprint('buildings', __name__, url_prefix='/buildings')


@bp.route('/')
@login_required
@role_required('admin', 'warehouse_staff')
def index():
    """Display all buildings - accessible by admin and warehouse staff only"""
    from app.models.facilities import UnitDetail
    buildings = Building.query.order_by(Building.code).all()

    # Get stats for each building
    building_stats = {}
    for building in buildings:
        # Room details for this building
        room_details = UnitDetail.query.filter_by(building_id=building.id).all()

        building_stats[building.id] = {
            'hq_count': 0,  # Units are no longer related to buildings
            'unit_count': 0,  # Units are no longer related to buildings
            'room_count': len(room_details),
            'has_zone': bool(building.zone_json)
        }

    return render_template('buildings/index.html', buildings=buildings, building_stats=building_stats)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create a new building - admin only"""
    form = BuildingForm()

    if form.validate_on_submit():
        try:
            building = Building(
                code=form.code.data,
                name=form.name.data,
                address=form.address.data,
                floor_count=form.floor_count.data if form.floor_count.data else 1
            )

            # Set coordinates if provided
            if form.latitude.data and form.longitude.data:
                building.set_coordinates(form.latitude.data, form.longitude.data)

            building.save()
            flash(f'Gedung {building.name} berhasil ditambahkan!', 'success')
            return redirect(url_for('buildings.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('buildings/form.html', form=form, action='create')


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit building - admin only"""
    building = Building.query.get_or_404(id)
    form = BuildingForm(obj=building)

    if form.validate_on_submit():
        try:
            building.code = form.code.data
            building.name = form.name.data
            building.address = form.address.data
            building.floor_count = form.floor_count.data if form.floor_count.data else 1

            # Update coordinates if provided
            if form.latitude.data and form.longitude.data:
                building.set_coordinates(form.latitude.data, form.longitude.data)
            else:
                building.geom = None

            db.session.commit()
            flash(f'Gedung {building.name} berhasil diperbarui!', 'success')
            return redirect(url_for('buildings.detail', building_id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('buildings/form.html', form=form, building=building, action='edit')


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete building - admin only"""
    from app.models.facilities import UnitDetail

    building = Building.query.get_or_404(id)

    # Check if there are any rooms in this building
    room_count = UnitDetail.query.filter_by(building_id=id).count()
    if room_count > 0:
        flash(f'Tidak dapat menghapus gedung {building.name} karena masih memiliki {room_count} ruangan. Silakan hapus ruangan terlebih dahulu.', 'warning')
        return redirect(url_for('buildings.detail', building_id=id))

    try:
        building.delete()
        flash(f'Gedung {building.name} berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('buildings.index'))


@bp.route('/<int:building_id>')
@login_required
@role_required('admin', 'warehouse_staff')
def detail(building_id):
    """Building detail page - accessible by admin and warehouse staff only"""
    from app.models.facilities import UnitDetail
    building = Building.query.get_or_404(building_id)

    # Get all rooms in this building
    rooms = UnitDetail.query.filter_by(building_id=building_id).order_by(UnitDetail.room_name).all()

    return render_template('buildings/detail.html', building=building, rooms=rooms, units=[])


@bp.route('/<int:building_id>/rooms/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_room(building_id):
    """Create a new room in building - admin only"""
    from app.models.facilities import UnitDetail

    building = Building.query.get_or_404(building_id)
    form = UnitDetailForm()

    # Set building_id as default and only choice
    form.building_id.choices = [(building.id, building.name)]

    if form.validate_on_submit():
        try:
            room = UnitDetail(
                building_id=building_id,
                room_name=form.room_name.data,
                floor=form.floor.data,
                description=form.description.data
            )
            room.save()
            flash(f'Ruangan {room.room_name} berhasil ditambahkan!', 'success')
            return redirect(url_for('buildings.detail', building_id=building_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('buildings/room_form.html', form=form, building=building, action='create')


@bp.route('/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_room(room_id):
    """Edit room - admin only"""
    from app.models.facilities import UnitDetail

    room = UnitDetail.query.get_or_404(room_id)
    building = Building.query.get_or_404(room.building_id)
    form = UnitDetailForm(obj=room)

    # Set building choices
    form.building_id.choices = [(b.id, b.name) for b in Building.query.order_by(Building.code).all()]

    if form.validate_on_submit():
        try:
            room.building_id = form.building_id.data
            room.room_name = form.room_name.data
            room.floor = form.floor.data
            room.description = form.description.data
            db.session.commit()
            flash(f'Ruangan {room.room_name} berhasil diperbarui!', 'success')
            return redirect(url_for('buildings.detail', building_id=room.building_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('buildings/room_form.html', form=form, building=building, room=room, action='edit')


@bp.route('/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_room(room_id):
    """Delete room - admin only"""
    from app.models.facilities import UnitDetail
    from app.models import Distribution

    room = UnitDetail.query.get_or_404(room_id)
    building_id = room.building_id

    # Check if there are any distributions using this room
    dist_count = Distribution.query.filter_by(unit_detail_id=room_id).count()
    if dist_count > 0:
        flash(f'Tidak dapat menghapus ruangan {room.room_name} karena masih ada {dist_count} distribusi yang terkait.', 'warning')
        return redirect(url_for('buildings.detail', building_id=building_id))

    try:
        room.delete()
        flash(f'Ruangan {room.room_name} berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('buildings.detail', building_id=building_id))


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


@bp.route('/rooms/<int:room_id>/items')
@login_required
def room_items(room_id):
    """API to get all distributed items in a specific room"""
    from app.models.facilities import UnitDetail
    from app.models import Distribution

    room = UnitDetail.query.get_or_404(room_id)

    # Get all distributions in this room with status 'installed'
    distributions = Distribution.query.filter_by(
        unit_detail_id=room_id,
        status='installed'
    ).all()

    items = []
    for dist in distributions:
        if dist.item_detail and dist.item_detail.item:
            # Use installed_at or created_at as distribution date
            dist_date = None
            if dist.installed_at:
                dist_date = dist.installed_at.strftime('%d/%m/%Y')
            elif dist.created_at:
                dist_date = dist.created_at.strftime('%d/%m/%Y')
            else:
                dist_date = '-'

            items.append({
                'id': dist.item_detail.id,
                'serial_number': dist.item_detail.serial_number,
                'item_name': dist.item_detail.item.name,
                'item_code': dist.item_detail.item.item_code,
                'category': dist.item_detail.item.category.name if dist.item_detail.item.category else '-',
                'distributed_date': dist_date
            })

    return jsonify({
        'success': True,
        'room_name': room.room_name,
        'building_name': room.building.name,
        'items_count': len(items),
        'items': items
    })
