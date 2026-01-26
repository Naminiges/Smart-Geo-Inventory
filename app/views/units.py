import json
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Unit, User, UserUnit, AssetRequest, Building
from app.forms.unit_forms import UnitForm
from app.utils.decorators import role_required
from sqlalchemy import or_

bp = Blueprint('units', __name__, url_prefix='/admin/units')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """List all units"""
    units = Unit.query.order_by(Unit.created_at.desc()).all()

    # Get statistics
    total_count = Unit.query.count()
    available_count = Unit.query.filter_by(status='available').count()
    in_use_count = Unit.query.filter_by(status='in_use').count()
    maintenance_count = Unit.query.filter_by(status='maintenance').count()

    return render_template('admin/units/index.html',
                         units=units,
                         stats={
                             'total': total_count,
                             'available': available_count,
                             'in_use': in_use_count,
                             'maintenance': maintenance_count
                         })


@bp.route('/loans')
@login_required
@role_required('admin')
def loans():
    """List venue loans for admin verification"""
    from app.models import VenueLoan

    status_filter = request.args.get('status', '')

    # Build query for venue loans
    query = VenueLoan.query

    # Status filter
    if status_filter:
        query = query.filter_by(status=status_filter)

    venue_loans = query.order_by(VenueLoan.created_at.desc()).all()

    # Get statistics
    total_count = VenueLoan.query.count()
    pending_count = VenueLoan.query.filter_by(status='pending').count()
    approved_count = VenueLoan.query.filter_by(status='approved').count()
    active_count = VenueLoan.query.filter_by(status='active').count()
    completed_count = VenueLoan.query.filter_by(status='completed').count()

    return render_template('admin/units/loans.html',
                         venue_loans=venue_loans,
                         status_filter=status_filter,
                         stats={
                             'total': total_count,
                             'pending': pending_count,
                             'approved': approved_count,
                             'active': active_count,
                             'completed': completed_count
                         })


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create new unit"""
    form = UnitForm()

    # Populate building choices
    buildings = Building.query.order_by(Building.code).all()
    form.building_id.choices = [(0, '-- Pilih Gedung --')] + [(b.id, f"{b.code} - {b.name}") for b in buildings]

    if form.validate_on_submit():
        try:
            # Create unit
            unit = Unit(
                name=form.name.data,
                address=form.address.data,
                status=form.status.data,
                building_id=form.building_id.data if form.building_id.data != 0 else None
            )

            # Set coordinates if provided
            if form.latitude.data and form.longitude.data:
                unit.set_coordinates(form.latitude.data, form.longitude.data)

            unit.save()
            flash(f'Unit {unit.name} berhasil dibuat!', 'success')
            return redirect(url_for('units.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/units/create.html', form=form)


@bp.route('/<int:id>')
@login_required
@role_required('admin')
def detail(id):
    """View unit detail"""
    unit = Unit.query.get_or_404(id)

    # Get asset requests for this unit
    asset_requests = AssetRequest.query.filter_by(unit_id=id).order_by(AssetRequest.created_at.desc()).all()

    return render_template('admin/units/detail.html',
                         unit=unit,
                         asset_requests=asset_requests)


@bp.route('/<int:id>/edit-zone', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_zone(id):
    """Edit unit zone"""
    unit = Unit.query.get_or_404(id)

    if request.method == 'POST':
        try:
            # Get zone data from form
            zone_coords = request.form.get('zone_coordinates')
            zone_kode = request.form.get('zone_kode', '')
            zone_deskripsi = request.form.get('zone_deskripsi', '')

            if zone_coords:
                # Parse and save zone data
                coords = json.loads(zone_coords)
                unit.zone_json = json.dumps({
                    "type": "Feature",
                    "properties": {
                        "nama": unit.name,
                        "kode_zona": zone_kode,
                        "deskripsi": zone_deskripsi
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
                })

                # Also update zona_kampus.json file
                json_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'zona_kampus.json')

                # Read existing data
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        geojson_data = json.load(f)
                else:
                    geojson_data = {"type": "FeatureCollection", "features": []}

                # Remove existing zone for this unit if any
                unit_feature_key = None
                for i, feature in enumerate(geojson_data['features']):
                    if feature['properties'].get('nama') == unit.name:
                        unit_feature_key = i
                        break

                # Create new feature
                new_feature = {
                    "type": "Feature",
                    "properties": {
                        "nama": unit.name,
                        "kode_zona": zone_kode,
                        "deskripsi": zone_deskripsi
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
                }

                # Update or add feature
                if unit_feature_key is not None:
                    geojson_data['features'][unit_feature_key] = new_feature
                else:
                    geojson_data['features'].append(new_feature)

                # Write back to file
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(geojson_data, f, indent=2, ensure_ascii=False)

                unit.save()
                flash(f'Zona {unit.name} berhasil diperbarui!', 'success')
            else:
                flash('Koordinat zona tidak valid', 'danger')

            return redirect(url_for('units.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/units/edit_zone.html', unit=unit)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit unit"""
    unit = Unit.query.get_or_404(id)
    form = UnitForm(obj=unit)

    # Populate building choices
    buildings = Building.query.order_by(Building.code).all()
    form.building_id.choices = [(0, '-- Pilih Gedung --')] + [(b.id, f"{b.code} - {b.name}") for b in buildings]

    # Pre-fill coordinates if available
    if request.method == 'GET':
        coordinates = unit.get_coordinates()
        if coordinates:
            form.latitude.data = coordinates['latitude']
            form.longitude.data = coordinates['longitude']
        # Set building_id
        if unit.building_id:
            form.building_id.data = unit.building_id
        else:
            form.building_id.data = 0

    if form.validate_on_submit():
        try:
            # Update unit
            unit.name = form.name.data
            unit.address = form.address.data
            unit.status = form.status.data
            unit.building_id = form.building_id.data if form.building_id.data != 0 else None

            # Update coordinates if provided
            if form.latitude.data and form.longitude.data:
                unit.set_coordinates(form.latitude.data, form.longitude.data)

            unit.save()
            flash(f'Unit {unit.name} berhasil diupdate!', 'success')
            return redirect(url_for('units.detail', id=id))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/units/edit.html', unit=unit, form=form)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete unit"""
    unit = Unit.query.get_or_404(id)

    try:
        # Check if unit has installations
        if unit.items_count > 0:
            flash(f'Tidak bisa menghapus unit yang masih memiliki {unit.items_count} item!', 'danger')
            return redirect(url_for('units.detail', id=id))

        # Delete unit
        unit.delete()
        flash(f'Unit {unit.name} berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('units.index'))


@bp.route('/<int:id>/assign-staffs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def assign_staffs(id):
    """Assign unit staff to unit"""
    unit = Unit.query.get_or_404(id)

    if request.method == 'POST':
        try:
            # Get selected staff (only unit_staff role)
            selected_staff_ids = request.form.getlist('staff_ids')

            # Remove old assignments
            UserUnit.query.filter_by(unit_id=id).delete()

            # Add new assignments
            for staff_id in selected_staff_ids:
                if staff_id:  # Make sure staff_id is not empty
                    user_unit = UserUnit(
                        user_id=staff_id,
                        unit_id=id,
                        assigned_by=current_user.id
                    )
                    db.session.add(user_unit)

            db.session.commit()
            flash(f'Staff assignment untuk {unit.name} berhasil diupdate!', 'success')
            return redirect(url_for('units.detail', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show form
    # Get only users with unit_staff role
    staffs = User.query.filter_by(role='unit_staff').all()
    current_assignments = [uu.user_id for uu in unit.user_units]

    return render_template('admin/units/assign_staffs.html',
                         unit=unit,
                         staffs=staffs,
                         current_assignments=current_assignments)


@bp.route('/api/save-zone', methods=['POST'])
@login_required
@role_required('admin')
def save_zone():
    """Save zone to zona_kampus.json"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['nama', 'kode_zona', 'deskripsi', 'coordinates']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400

        # Create new feature
        new_feature = {
            "type": "Feature",
            "properties": {
                "nama": data['nama'],
                "kode_zona": data['kode_zona'],
                "deskripsi": data['deskripsi']
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [data['coordinates']]
            }
        }

        # Path to zona_kampus.json
        json_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'zona_kampus.json')

        # Read existing data
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
        else:
            geojson_data = {
                "type": "FeatureCollection",
                "features": []
            }

        # Add new feature
        geojson_data['features'].append(new_feature)

        # Write back to file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'message': 'Zona berhasil disimpan!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

