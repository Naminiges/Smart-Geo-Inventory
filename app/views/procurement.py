from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Procurement, Supplier, Item, User, Warehouse, Category
from app.models.procurement import ProcurementItem
from app.forms import (
    ProcurementRequestForm,
    ProcurementApprovalForm,
    GoodsReceiptForm,
    ProcurementCompleteForm
)
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('procurement', __name__, url_prefix='/procurement')


@bp.route('/')
@login_required
@role_required('admin', 'warehouse_staff')
def index():
    """List all procurements"""
    status_filter = request.args.get('status', '')
    query = Procurement.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    procurements = query.order_by(Procurement.created_at.desc()).all()

    # Get statistics
    total_procurements = Procurement.query.count()
    pending_count = Procurement.query.filter_by(status='pending').count()
    approved_count = Procurement.query.filter_by(status='approved').count()
    received_count = Procurement.query.filter_by(status='received').count()
    completed_count = Procurement.query.filter_by(status='completed').count()

    return render_template('procurement/index.html',
                         procurements=procurements,
                         stats={
                             'total': total_procurements,
                             'pending': pending_count,
                             'approved': approved_count,
                             'received': received_count,
                             'completed': completed_count
                         },
                         current_filter=status_filter)


@bp.route('/request', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse_staff')
def create_request():
    """Create procurement request - different behavior based on role:
    - Admin: Creates directly approved procurement
    - Warehouse Staff: Creates pending request that needs admin approval
    """
    is_admin = current_user.is_admin()
    return _create_procurement_request(is_admin=is_admin)


def _create_procurement_request(is_admin=False):
    """
    Shared function for creating procurement requests.
    - Warehouse staff: Creates with 'pending' status, needs admin approval
    - Admin: Creates directly with 'approved' status, no approval needed
    """
    form = ProcurementRequestForm()

    if request.method == 'POST':
        try:
            # Get items data from form
            items_data = request.form.getlist('items')
            request_notes = form.request_notes.data

            # For admin: Get supplier and warehouse
            if is_admin:
                supplier_id = request.form.get('supplier_id', type=int)
                warehouse_id = request.form.get('warehouse_id', type=int)

                if not supplier_id:
                    flash('Silakan pilih supplier!', 'danger')
                    return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all(), warehouses=Warehouse.query.all(), is_admin=is_admin)

                if not warehouse_id:
                    flash('Silakan pilih warehouse tujuan!', 'danger')
                    return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all(), warehouses=Warehouse.query.all(), is_admin=is_admin)

            if not items_data or len(items_data) == 0:
                flash('Minimal harus ada satu barang yang diminta!', 'danger')
                return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all() if is_admin else [], warehouses=Warehouse.query.all() if is_admin else [], is_admin=is_admin)

            # Validate and process items
            valid_items = []
            for item_json in items_data:
                import json
                item_data = json.loads(item_json)

                # Check if user selected existing item or new item
                if item_data.get('item_id') == -1:
                    # Barang baru - langsung buat item baru di tabel items
                    if not item_data.get('item_name'):
                        flash('Nama barang baru harus diisi!', 'danger')
                        return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all() if is_admin else [], warehouses=Warehouse.query.all() if is_admin else [], is_admin=is_admin)

                    if not item_data.get('item_category_id') or item_data.get('item_category_id') == 0:
                        flash('Kategori barang harus dipilih!', 'danger')
                        return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all() if is_admin else [], warehouses=Warehouse.query.all() if is_admin else [], is_admin=is_admin)

                    # Buat item baru langsung di tabel items
                    new_item = Item(
                        name=item_data.get('item_name'),
                        item_code=f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(valid_items)}",
                        category_id=item_data.get('item_category_id'),
                        unit=item_data.get('item_unit') or 'pcs'
                    )
                    new_item.save()

                    # Add to valid items with the new item_id
                    valid_items.append({
                        'item_id': new_item.id,
                        'quantity': item_data.get('quantity'),
                        'is_new_item': False  # Already created
                    })
                else:
                    # Barang existing
                    if not item_data.get('item_id') or item_data.get('item_id') == 0:
                        flash('Harap pilih barang dari daftar atau pilih "Lainnya"', 'danger')
                        return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all() if is_admin else [], warehouses=Warehouse.query.all() if is_admin else [], is_admin=is_admin)

                    valid_items.append({
                        'item_id': item_data.get('item_id'),
                        'quantity': item_data.get('quantity'),
                        'is_new_item': False
                    })

            if not valid_items:
                flash('Tidak ada barang valid yang diminta!', 'danger')
                return render_template('procurement/request.html', form=form, items=Item.query.all(), categories=Category.query.all(), suppliers=Supplier.query.all() if is_admin else [], warehouses=Warehouse.query.all() if is_admin else [], is_admin=is_admin)

            # Create procurement
            if is_admin:
                # Admin creates procurement - directly approved
                procurement = Procurement(
                    request_notes=request_notes,
                    status='approved',  # Directly approved
                    requested_by=current_user.id,
                    request_date=datetime.now(),
                    supplier_id=supplier_id,
                    approved_by=current_user.id,
                    approval_date=datetime.now(),
                    warehouse_id=warehouse_id  # Set warehouse tujuan
                )
                procurement.save()

                success_message = f'Pengadaan berhasil dibuat dan disetujui dengan {len(valid_items)} barang! Supplier: {procurement.supplier.name if procurement.supplier else "N/A"}'
            else:
                # Warehouse staff creates procurement - needs approval
                procurement = Procurement(
                    request_notes=request_notes,
                    status='pending',  # Needs admin approval
                    requested_by=current_user.id,
                    request_date=datetime.now()
                )
                procurement.save()

                success_message = f'Permohonan pengadaan berhasil dibuat dengan {len(valid_items)} barang! Menunggu persetujuan admin.'

            # Create procurement items
            for item_data in valid_items:
                procurement_item = ProcurementItem(
                    procurement_id=procurement.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity']
                )
                procurement_item.save()

            flash(success_message, 'success')
            return redirect(url_for('procurement.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - prepare data for template
    items = Item.query.all()
    categories = Category.query.all()
    suppliers = Supplier.query.all() if is_admin else []
    warehouses = Warehouse.query.all() if is_admin else []

    # Use same template for both admin and warehouse staff
    return render_template('procurement/request.html',
                         form=form,
                         items=items,
                         categories=categories,
                         suppliers=suppliers,
                         warehouses=warehouses,
                         is_admin=is_admin)


@bp.route('/<int:id>')
@login_required
@role_required('admin', 'warehouse_staff')
def detail(id):
    """View procurement detail"""
    procurement = Procurement.query.get_or_404(id)
    return render_template('procurement/detail.html', procurement=procurement)


@bp.route('/<int:id>/approve', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def approve(id):
    """Step 3: Admin approves and selects supplier"""
    procurement = Procurement.query.get_or_404(id)

    if procurement.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa disetujui.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    form = ProcurementApprovalForm()
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]

    if form.validate_on_submit():
        try:
            success, message = procurement.approve(
                user_id=current_user.id,
                supplier_id=form.supplier_id.data
            )

            if success:
                if form.notes.data:
                    procurement.notes = form.notes.data
                procurement.save()

                flash(f'{message} Supplier telah dipilih.', 'success')
                return redirect(url_for('procurement.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('procurement/approve.html', procurement=procurement, form=form)


@bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject(id):
    """Reject procurement request"""
    procurement = Procurement.query.get_or_404(id)
    rejection_reason = request.form.get('rejection_reason', '')

    try:
        success, message = procurement.reject(current_user.id, rejection_reason)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('procurement.detail', id=id))


@bp.route('/<int:id>/receive', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff')
def receive_goods(id):
    """Step 4-5: Record goods receipt with single invoice and multiple deliveries for multiple items"""
    procurement = Procurement.query.get_or_404(id)

    if procurement.status != 'approved' and procurement.status != 'received':
        flash('Hanya pengadaan yang sudah disetujui yang bisa menerima barang.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    form = GoodsReceiptForm()

    # Pre-fill invoice number if already exists (subsequent deliveries)
    if procurement.receipt_number and not form.receipt_number.data:
        form.receipt_number.data = procurement.receipt_number

    if form.validate_on_submit():
        try:
            from app.models.master_data import ItemDetail, Item
            import json

            # Prepare items data from form
            items_data = []
            for procurement_item in procurement.items:
                quantity_key = f'quantity_{procurement_item.id}'
                serials_key = f'serial_numbers_{procurement_item.id}'
                serial_units_key = f'serial_units_{procurement_item.id}'

                quantity_received = request.form.get(quantity_key, type=int)
                serial_numbers_str = request.form.get(serials_key, '')
                serial_units_str = request.form.get(serial_units_key, '')

                # Skip if no quantity provided
                if not quantity_received or quantity_received <= 0:
                    continue

                # Determine if this is networking/server category
                category_name = procurement_item.item.category.name.lower() if procurement_item.item and procurement_item.item.category else ''
                is_networking = any(keyword in category_name for keyword in ['jaringan', 'network', 'server'])

                # Auto-generate serial units for ALL items (both networking and non-networking)
                item_code = procurement_item.item.item_code if procurement_item.item else 'ITEM'

                # Get the last serial unit for this item to continue the sequence
                last_serial_unit = ItemDetail.query.filter(
                    ItemDetail.serial_unit.like(f'{item_code}-%')
                ).order_by(ItemDetail.serial_unit.desc()).first()

                start_num = 1
                if last_serial_unit and last_serial_unit.serial_unit:
                    try:
                        last_num = int(last_serial_unit.serial_unit.split('-')[-1])
                        start_num = last_num + 1
                    except:
                        start_num = 1

                # Generate serial units
                serial_units = []
                for i in range(quantity_received):
                    serial_unit = f"{item_code}-{str(start_num + i).zfill(3)}"
                    serial_units.append(serial_unit)

                # For networking items: require manual serial numbers
                if is_networking:
                    serial_numbers = []
                    if serial_numbers_str:
                        serial_numbers = [sn.strip() for sn in serial_numbers_str.split('\n') if sn.strip()]

                    # Validate quantity matches serial numbers count for networking items
                    if len(serial_numbers) != quantity_received:
                        flash(f'{procurement_item.item.name if procurement_item.item else "Item"}: Jumlah serial number ({len(serial_numbers)}) harus sama dengan jumlah barang ({quantity_received}) untuk kategori jaringan!', 'warning')
                        return render_template('procurement/receive.html', procurement=procurement, form=form)

                    # Check for duplicate serial numbers
                    existing_serials = ItemDetail.query.filter(
                        ItemDetail.serial_number.in_(serial_numbers)
                    ).all()
                    if existing_serials:
                        existing_list = [sn.serial_number for sn in existing_serials]
                        flash(f'{procurement_item.item.name if procurement_item.item else "Item"}: Serial number sudah terdaftar: {", ".join(existing_list)}', 'warning')
                        return render_template('procurement/receive.html', procurement=procurement, form=form)
                else:
                    # For non-networking items: use serial_units as serial_numbers (both fields same)
                    serial_numbers = serial_units

                items_data.append({
                    'procurement_item_id': procurement_item.id,
                    'quantity_received': quantity_received,
                    'serial_numbers': serial_numbers,  # Manual for networking, auto-generated for non-networking
                    'serial_units': serial_units  # Always auto-generated
                })

            if not items_data:
                flash('Minimal harus ada satu barang yang diterima!', 'warning')
                return render_template('procurement/receive.html', procurement=procurement, form=form)

            success, message = procurement.receive_goods(
                user_id=current_user.id,
                receipt_number=form.receipt_number.data,
                items_data=items_data
            )

            if success:
                # Check if fully received
                if procurement.is_fully_received:
                    flash(f'{message} Semua barang sudah lengkap! Siap untuk diselesaikan.', 'success')
                else:
                    flash(f'{message} Anda bisa melakukan penerimaan lagi untuk sisa barang.', 'info')
                return redirect(url_for('procurement.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('procurement/receive.html', procurement=procurement, form=form)


@bp.route('/<int:id>/complete', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff')
def complete(id):
    """Step 6: Complete procurement and add to stock - only if fully received"""
    from app.models.user import UserWarehouse

    procurement = Procurement.query.get_or_404(id)

    # Validasi: harus status received dan semua barang sudah diterima
    if not procurement.is_fully_received:
        flash(f'Pengadaan belum bisa diselesaikan. Barang yang diterima baru {procurement.total_received}/{procurement.total_quantity} unit. Masih kurang {procurement.remaining_quantity} unit.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    if procurement.status not in ['received']:
        flash('Hanya pengadaan yang sudah menerima barang dan lengkap yang bisa diselesaikan.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    # Get warehouse dari user yang login (warehouse staff)
    user_warehouse = UserWarehouse.query.filter_by(user_id=current_user.id).first()

    if not user_warehouse:
        flash('Anda belum terassign ke warehouse manapun. Hubungi admin.', 'danger')
        return redirect(url_for('procurement.detail', id=id))

    warehouse_id = user_warehouse.warehouse_id

    if request.method == 'POST':
        try:
            success, message = procurement.complete(
                user_id=current_user.id,
                warehouse_id=warehouse_id
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('procurement.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('procurement/complete.html',
                         procurement=procurement,
                         warehouse=user_warehouse.warehouse)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete procurement request"""
    procurement = Procurement.query.get_or_404(id)

    if procurement.status not in ['pending', 'rejected']:
        flash('Hanya permohonan dengan status pending atau rejected yang bisa dihapus.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    try:
        procurement.delete()
        flash('Pengadaan berhasil dihapus.', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('procurement.index'))
