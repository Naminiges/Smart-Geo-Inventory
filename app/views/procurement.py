from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Procurement, Supplier, Item, User, Warehouse, Category
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
@role_required('warehouse_staff')
def create_request():
    """Step 1-2: Warehouse staff creates procurement request"""
    form = ProcurementRequestForm()

    # Populate item choices with "Lainnya" option
    form.item_id.choices = [(0, '-- Pilih dari daftar barang --')] + \
                          [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()] + \
                          [(-1, 'Lainnya (Barang Baru)')]

    # Populate category choices
    form.item_category_id.choices = [(0, '-- Pilih Kategori --')] + \
                                   [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        try:
            # Check if user selected "Lainnya"
            if form.item_id.data == -1:
                # Barang baru - langsung buat item baru di tabel items
                if not form.item_name.data:
                    flash('Nama barang baru harus diisi!', 'danger')
                    return render_template('procurement/request.html', form=form)

                if not form.item_category_id.data or form.item_category_id.data == 0:
                    flash('Kategori barang harus dipilih!', 'danger')
                    return render_template('procurement/request.html', form=form)

                # Buat item baru langsung di tabel items
                new_item = Item(
                    name=form.item_name.data,
                    item_code=f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    category_id=form.item_category_id.data,
                    unit=form.item_unit.data or 'pcs'
                )
                new_item.save()

                # Buat procurement dengan item_id yang baru dibuat
                procurement = Procurement(
                    item_id=new_item.id,  # Pakai item yang baru dibuat
                    quantity=form.quantity.data,
                    request_notes=form.request_notes.data,
                    status='pending',
                    requested_by=current_user.id,
                    request_date=datetime.now()
                )
                procurement.save()

                flash(f'Permohonan pengadaan berhasil dibuat! Barang baru "{new_item.name}" telah ditambahkan ke katalog. Menunggu persetujuan admin.', 'success')
            else:
                # Barang existing
                if not form.item_id.data or form.item_id.data == 0:
                    flash('Harap pilih barang dari daftar atau pilih "Lainnya"', 'danger')
                    return render_template('procurement/request.html', form=form)

                procurement = Procurement(
                    item_id=form.item_id.data,
                    quantity=form.quantity.data,
                    request_notes=form.request_notes.data,
                    status='pending',
                    requested_by=current_user.id,
                    request_date=datetime.now()
                )
                procurement.save()

                flash('Permohonan pengadaan berhasil dibuat! Menunggu persetujuan admin.', 'success')

            return redirect(url_for('procurement.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('procurement/request.html', form=form)


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
                procurement.unit_price = form.unit_price.data
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
    """Step 4-5: Record goods receipt with single invoice and multiple deliveries"""
    procurement = Procurement.query.get_or_404(id)

    if procurement.status != 'approved' and procurement.status != 'received':
        flash('Hanya pengadaan yang sudah disetujui yang bisa menerima barang.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    form = GoodsReceiptForm()

    # Pre-fill invoice number if already exists (subsequent deliveries)
    if procurement.receipt_number and not form.receipt_number.data:
        form.receipt_number.data = procurement.receipt_number

    # Set default actual_quantity to remaining quantity for partial receive
    if not form.actual_quantity.data:
        form.actual_quantity.data = procurement.remaining_quantity

    if form.validate_on_submit():
        try:
            # Parse serial numbers from textarea
            serial_numbers = []
            if form.serial_numbers.data:
                serial_numbers = [sn.strip() for sn in form.serial_numbers.data.split('\n') if sn.strip()]

            # Validate serial numbers count
            quantity_received = form.actual_quantity.data
            if len(serial_numbers) > 0 and len(serial_numbers) != quantity_received:
                flash(f'Jumlah serial number ({len(serial_numbers)}) harus sama dengan jumlah barang ({quantity_received})!', 'warning')
                return render_template('procurement/receive.html', procurement=procurement, form=form)

            # Validate: tidak boleh melebihi quantity yang diminta
            if procurement.total_received + quantity_received > procurement.quantity:
                flash(f'Total barang yang diterima ({procurement.total_received + quantity_received}) tidak boleh melebihi jumlah yang diminta ({procurement.quantity})!', 'warning')
                return render_template('procurement/receive.html', procurement=procurement, form=form)

            success, message = procurement.receive_goods(
                user_id=current_user.id,
                receipt_number=form.receipt_number.data,
                quantity_received=quantity_received,
                serial_numbers=serial_numbers if serial_numbers else None
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
    procurement = Procurement.query.get_or_404(id)

    # Validasi: harus status received dan semua barang sudah diterima
    if not procurement.is_fully_received:
        flash(f'Pengadaan belum bisa diselesaikan. Barang yang diterima baru {procurement.total_received}/{procurement.quantity} unit. Masih kurang {procurement.remaining_quantity} unit.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    if procurement.status not in ['received']:
        flash('Hanya pengadaan yang sudah menerima barang dan lengkap yang bisa diselesaikan.', 'warning')
        return redirect(url_for('procurement.detail', id=id))

    form = ProcurementCompleteForm()
    form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    if form.validate_on_submit():
        try:
            success, message = procurement.complete(
                user_id=current_user.id,
                warehouse_id=form.warehouse_id.data
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('procurement.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('procurement/complete.html', procurement=procurement, form=form)


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
