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
    form.transfer_type.data = 'room'  # Default: pindah ruangan

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
        print(f"transfer_type.data: {form.transfer_type.data} (type: {type(form.transfer_type.data)})")
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

    print(f"\n=== REQUEST INFO ===")
    print(f"Method: {request.method}")
    print(f"Form validate on submit: {form.validate_on_submit()}")
    if request.method == 'POST':
        print(f"Form data: {dict(request.form)}")
        print(f"Form data.raw: {list(request.form.items())}")
    if not form.validate_on_submit() and request.method == 'POST':
        print(f"Form errors: {form.errors}")
        print(f"CSRF token: {request.form.get('csrf_token')}")
    print(f"===================\n")

    if request.method == 'POST' and form.validate_on_submit():
        try:
            # DEBUGGING: Log form data
            print("\n=== FORM SUBMISSION DEBUG ===")
            print(f"Request form data: {dict(request.form)}")
            print(f"source_unit_id.data: {form.source_unit_id.data}")
            print(f"transfer_type.data: {form.transfer_type.data}")
            print(f"target_unit_id.data: {form.target_unit_id.data}")
            print(f"target_unit_detail_id.data: {form.target_unit_detail_id.data}")
            print("============================\n")

            # Ambil data dari form
            source_unit_id = form.source_unit_id.data
            # Baca transfer_type dari request.form karena hidden input lebih reliable
            transfer_type = request.form.get('transfer_type', 'room')
            print(f"Using transfer_type from request.form: {transfer_type}")

            # Get selected items from hidden input
            selected_items_str = request.form.get('selected_items', '')
            if not selected_items_str:
                flash('Silakan pilih minimal satu barang untuk dipindahkan', 'warning')
                return redirect(url_for('asset_transfer.create'))

            selected_item_ids = [int(id.strip()) for id in selected_items_str.split(',') if id.strip()]
            print(f"Selected item IDs: {selected_item_ids}")

            if not selected_item_ids:
                flash('Tidak ada barang yang valid dipilih', 'danger')
                return redirect(url_for('asset_transfer.create'))

            # Tentukan target unit dan room berdasarkan transfer_type
            target_unit_id = None
            target_unit_detail_id = None

            # DEBUG: Log semua form data
            print(f"\n=== FORM SUBMISSION DEBUG ===")
            print(f"Transfer Type: {transfer_type}")
            print(f"All form keys: {list(request.form.keys())}")
            print(f"All form values: {dict(request.form)}")

            if transfer_type == 'room':
                # Pindah ruangan saja - tetap di unit yang sama
                target_unit_id = source_unit_id
                # Baca dari field khusus tab room
                target_unit_detail_id = request.form.get('target_unit_detail_id_room', type=int)
                print(f"[ROOM TRANSFER] target_unit_detail_id_room: {target_unit_detail_id}")
            elif transfer_type == 'unit':
                # Pindah unit saja - hanya unit_id yang berubah, unit_detail_id TETAP
                target_unit_id = request.form.get('target_unit_id_unit', type=int)
                # unit_detail_id akan tetap sama untuk semua barang (tidak berubah)
                print(f"[UNIT TRANSFER] target_unit_id_unit: {target_unit_id}")
            else:  # both
                # Pindah lengkap - unit dan ruangan baru
                # Baca dari field khusus tab both
                target_unit_id = request.form.get('target_unit_id_both', type=int)
                target_unit_detail_id = request.form.get('target_unit_detail_id_both', type=int)
                print(f"[BOTH TRANSFER] target_unit_id_both: {target_unit_id}, target_unit_detail_id_both: {target_unit_detail_id}")

            print(f"FINAL VALUES - transfer_type: {transfer_type}, target_unit_id: {target_unit_id}, target_unit_detail_id: {target_unit_detail_id}")
            print(f"===================================\n")

            # Validasi nilai 0 (placeholder) dan None
            if source_unit_id == 0:
                flash('Silakan pilih unit asal', 'warning')
                return redirect(url_for('asset_transfer.create'))

            # Validasi berdasarkan transfer_type
            if transfer_type == 'room':
                if not target_unit_detail_id or target_unit_detail_id == 0:
                    flash('Silakan pilih ruangan tujuan', 'warning')
                    return redirect(url_for('asset_transfer.create'))
            elif transfer_type == 'unit':
                if not target_unit_id or target_unit_id == 0:
                    flash('Silakan pilih unit tujuan', 'warning')
                    return redirect(url_for('asset_transfer.create'))
            else:  # both
                if not target_unit_id or target_unit_id == 0:
                    flash('Silakan pilih unit tujuan', 'warning')
                    return redirect(url_for('asset_transfer.create'))
                if not target_unit_detail_id or target_unit_detail_id == 0:
                    flash('Silakan pilih ruangan tujuan', 'warning')
                    return redirect(url_for('asset_transfer.create'))

            # Process each selected item
            transferred_count = 0
            failed_items = []

            for item_detail_id in selected_item_ids:
                # Get distribution yang akan dipindahkan
                distribution = Distribution.query.filter_by(
                    item_detail_id=item_detail_id,
                    unit_id=source_unit_id,
                    status='installed'
                ).first()

                if not distribution:
                    failed_items.append(f"Item ID {item_detail_id} tidak ditemukan")
                    continue

                # Tentukan target berdasarkan transfer_type
                if transfer_type == 'room':
                    # Pindah ruangan: hanya unit_detail_id yang berubah
                    final_target_unit_id = source_unit_id  # Tetap di unit yang sama
                    final_target_unit_detail_id = target_unit_detail_id
                elif transfer_type == 'unit':
                    # Pindah unit: hanya unit_id yang berubah, unit_detail_id TETAP
                    final_target_unit_id = target_unit_id
                    final_target_unit_detail_id = distribution.unit_detail_id  # TETAP sama
                else:  # both
                    # Pindah lengkap: keduanya berubah
                    final_target_unit_id = target_unit_id
                    final_target_unit_detail_id = target_unit_detail_id

                # Validasi - cek apakah pindah ke lokasi yang sama
                if (distribution.unit_id == final_target_unit_id and
                    distribution.unit_detail_id == final_target_unit_detail_id):
                    failed_items.append(f"{distribution.item_detail.serial_number} sudah di lokasi tujuan")
                    continue

                # Simpan lokasi asal untuk history
                from_unit_id = distribution.unit_id
                from_unit_detail_id = distribution.unit_detail_id

                # UPDATE distribution ke lokasi baru (tetap status 'installed')
                distribution.unit_id = final_target_unit_id
                distribution.unit_detail_id = final_target_unit_detail_id
                distribution.updated_at = datetime.utcnow()

                # CATAT di asset_transfer (history/log saja)
                transfer = AssetTransfer(
                    item_detail_id=item_detail_id,
                    from_unit_id=from_unit_id,
                    from_unit_detail_id=from_unit_detail_id,
                    to_unit_id=final_target_unit_id,
                    to_unit_detail_id=final_target_unit_detail_id,
                    notes=form.notes.data,
                    transfer_date=datetime.utcnow(),
                    transferred_by=current_user.id
                )

                db.session.add(transfer)
                transferred_count += 1

            # Commit semua perubahan
            db.session.commit()

            # Show success/error message
            if failed_items:
                if transferred_count > 0:
                    flash(f'{transferred_count} barang berhasil dipindahkan. Namun {len(failed_items)} gagal: {", ".join(failed_items[:3])}', 'warning')
                else:
                    flash(f'Gagal memindahkan barang: {", ".join(failed_items[:3])}', 'danger')
            else:
                flash(f'{transferred_count} barang berhasil dipindahkan!', 'success')

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


@bp.route('/api/units')
@login_required
def api_all_units():
    """Get all units (for dropdown)"""
    try:
        units = Unit.query.order_by(Unit.name).all()

        units_data = []
        for u in units:
            units_data.append({
                'id': u.id,
                'name': u.name
            })

        return jsonify({'success': True, 'units': units_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/unit/<int:unit_id>/rooms')
@login_required
def api_unit_rooms(unit_id):
    """Get all rooms for a specific unit"""
    try:
        # Get unit details for this unit
        unit_details = UnitDetail.query.filter_by(unit_id=unit_id).join(Building).order_by(Building.code, UnitDetail.room_name).all()

        rooms_data = []
        for r in unit_details:
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
