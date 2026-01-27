"""
Asset Transfer Controller - Pemindahan barang antar unit/ruangan
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Distribution, Unit, UnitDetail, AssetTransfer, ItemDetail, Building
from app.forms import AssetTransferForm
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('asset_transfer', __name__, url_prefix='/asset-transfer')


@bp.route('/')
@login_required
@role_required('admin', 'warehouse_staff')
def index():
    """List history pemindahan barang"""
    transfers = AssetTransfer.query.order_by(AssetTransfer.created_at.desc()).all()
    return render_template('asset_transfer/index.html', transfers=transfers)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse_staff')
def create():
    """Form pemindahan barang antar unit/ruangan"""
    form = AssetTransferForm()

    # Populate units
    units = Unit.query.all()
    form.source_unit_id.choices = [(0, '-- Pilih Unit Asal --')] + [(u.id, u.name) for u in units]
    form.target_unit_id.choices = [(0, '-- Pilih Unit Tujuan --')] + [(u.id, u.name) for u in units]
    form.target_same_unit.data = 'no'  # Default: beda unit

    # ALWAYS populate source_item_detail_id choices with ALL possible items (for WTForms validation)
    # We need to include ALL installed items from ALL units so validation works
    all_distributions = Distribution.query.filter_by(status='installed').all()
    source_item_choices = [(0, '-- Pilih Barang --')]
    for dist in all_distributions:
        if dist.item_detail and dist.item_detail.item:
            label = f"{dist.item_detail.item.name} ({dist.item_detail.serial_number})"
            source_item_choices.append((dist.item_detail.id, label))
    form.source_item_detail_id.choices = source_item_choices

    # ALWAYS populate target_unit_detail_id choices (for WTForms validation)
    rooms_data = UnitDetail.query.join(Building).order_by(Building.code, UnitDetail.room_name).all()
    room_choices = [(0, '-- Pilih Ruangan Tujuan --')]
    for r in rooms_data:
        label = f"{r.building.code} - {r.room_name}"
        room_choices.append((r.id, label))
    form.target_unit_detail_id.choices = room_choices

    # If POST request with errors, repopulate source item choices based on selected unit
    if request.method == 'POST' and not form.validate_on_submit():
        # DEBUGGING: Log form validation errors
        print("\n=== FORM VALIDATION FAILED ===")
        print(f"Request form data: {dict(request.form)}")
        print(f"source_unit_id.data: {form.source_unit_id.data} (type: {type(form.source_unit_id.data)})")
        print(f"source_item_detail_id.data: {form.source_item_detail_id.data} (type: {type(form.source_item_detail_id.data)})")
        print(f"target_same_unit.data: {form.target_same_unit.data} (type: {type(form.target_same_unit.data)})")
        print(f"target_unit_id.data: {form.target_unit_id.data} (type: {type(form.target_unit_id.data)})")
        print(f"target_unit_detail_id.data: {form.target_unit_detail_id.data} (type: {type(form.target_unit_detail_id.data)})")
        print(f"Form errors: {form.errors}")
        print("==============================\n")

        # Restore source item choices if source unit was selected
        if form.source_unit_id.data and form.source_unit_id.data != 0:
            source_items_data = Distribution.query.filter_by(
                unit_id=form.source_unit_id.data,
                status='installed'
            ).all()

            source_item_choices = [(0, '-- Pilih Barang --')]
            for dist in source_items_data:
                if dist.item_detail and dist.item_detail.item:
                    label = f"{dist.item_detail.item.name} ({dist.item_detail.serial_number})"
                    source_item_choices.append((dist.item_detail.id, label))

            form.source_item_detail_id.choices = source_item_choices

    if request.method == 'POST' and form.validate_on_submit():
        try:
            # DEBUGGING: Log form data
            print("\n=== FORM SUBMISSION DEBUG ===")
            print(f"Request form data: {dict(request.form)}")
            print(f"source_unit_id.data: {form.source_unit_id.data} (type: {type(form.source_unit_id.data)})")
            print(f"source_item_detail_id.data: {form.source_item_detail_id.data} (type: {type(form.source_item_detail_id.data)})")
            print(f"target_same_unit.data: {form.target_same_unit.data} (type: {type(form.target_same_unit.data)})")
            print(f"target_unit_id.data: {form.target_unit_id.data} (type: {type(form.target_unit_id.data)})")
            print(f"target_unit_detail_id.data: {form.target_unit_detail_id.data} (type: {type(form.target_unit_detail_id.data)})")
            print(f"Form errors: {form.errors}")
            print("============================\n")

            # Ambil data dari form
            source_unit_id = form.source_unit_id.data
            source_item_detail_id = form.source_item_detail_id.data
            target_same_unit = form.target_same_unit.data
            target_unit_id = form.target_unit_id.data if target_same_unit == 'no' else source_unit_id
            target_unit_detail_id = form.target_unit_detail_id.data

            # Validasi nilai 0 (placeholder)
            if source_unit_id == 0 or source_item_detail_id == 0 or target_unit_detail_id == 0:
                flash('Silakan lengkapi semua field yang diperlukan', 'warning')
                return redirect(url_for('asset_transfer.create'))

            # Get distribution yang akan dipindahkan
            distribution = Distribution.query.filter_by(
                item_detail_id=source_item_detail_id,
                unit_id=source_unit_id,
                status='installed'
            ).first()

            if not distribution:
                flash('Barang tidak ditemukan atau status tidak valid untuk dipindahkan', 'danger')
                return redirect(url_for('asset_transfer.create'))

            # Validasi - cek apakah pindah ke lokasi yang sama
            if (distribution.unit_id == target_unit_id and
                distribution.unit_detail_id == target_unit_detail_id):
                flash('Tidak bisa memindahkan ke lokasi yang sama!', 'warning')
                return redirect(url_for('asset_transfer.create'))

            # Simpan lokasi asal untuk history
            from_unit_id = distribution.unit_id
            from_unit_detail_id = distribution.unit_detail_id

            # UPDATE distribution ke lokasi baru (tetap status 'installed')
            distribution.unit_id = target_unit_id
            distribution.unit_detail_id = target_unit_detail_id
            distribution.updated_at = datetime.utcnow()

            # CATAT di asset_transfer (history/log saja)
            transfer = AssetTransfer(
                item_detail_id=source_item_detail_id,
                from_unit_id=from_unit_id,
                from_unit_detail_id=from_unit_detail_id,
                to_unit_id=target_unit_id,
                to_unit_detail_id=target_unit_detail_id,
                notes=form.notes.data,
                transfer_date=datetime.utcnow(),
                transferred_by=current_user.id
            )

            db.session.add(transfer)
            db.session.commit()

            flash(f'Barang {distribution.item_detail.serial_number} berhasil dipindahkan!', 'success')
            return redirect(url_for('asset_transfer.index'))

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_transfer/create.html', form=form)


@bp.route('/api/unit/<int:unit_id>/items')
@login_required
def api_unit_items(unit_id):
    """Get all items currently installed in a unit"""
    try:
        distributions = Distribution.query.filter_by(
            unit_id=unit_id,
            status='installed'
        ).all()

        items = []
        for dist in distributions:
            if dist.item_detail and dist.item_detail.item:
                items.append({
                    'id': dist.item_detail.id,
                    'serial_number': dist.item_detail.serial_number,
                    'item_name': dist.item_detail.item.name,
                    'current_room': f"{dist.unit_detail.building.code} - {dist.unit_detail.room_name}" if dist.unit_detail else '-',
                    'unit_detail_id': dist.unit_detail_id
                })

        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/rooms')
@login_required
def api_all_rooms():
    """Get all rooms from all buildings (for dropdown)"""
    try:
        rooms = UnitDetail.query.join(Building).order_by(Building.code, UnitDetail.room_name).all()

        rooms_data = []
        for r in rooms:
            rooms_data.append({
                'id': r.id,
                'unit_detail_id': r.id,
                'label': f"{r.building.code} - {r.room_name}",
                'building_code': r.building.code,
                'room_name': r.room_name
            })

        return jsonify({'success': True, 'rooms': rooms_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
