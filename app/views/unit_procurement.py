from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (
    UnitProcurement, UnitProcurementItem, Unit,
    Item, User, Warehouse, Category, Procurement, ProcurementItem
)
from app.forms.unit_procurement_forms import (
    UnitProcurementRequestForm,
    UnitProcurementVerifyForm,
    UnitProcurementApproveForm,
    UnitProcurementRejectForm
)
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('unit_procurement', __name__, url_prefix='/unit-procurement')


def generate_item_code(category_id):
    """Generate item code based on category code"""
    category = Category.query.get(category_id)
    if not category or not category.code:
        # Fallback if category has no code
        return f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    prefix = category.code.upper()

    # Find the last item code with this prefix
    last_item = Item.query.filter(Item.item_code.like(f'{prefix}-%')).order_by(Item.item_code.desc()).first()

    if last_item and last_item.item_code:
        # Extract the number from the last item code (e.g., JAR-001 -> 001)
        try:
            last_number = int(last_item.item_code.split('-')[1])
            new_number = last_number + 1
        except (IndexError, ValueError):
            new_number = 1
    else:
        new_number = 1

    # Format: PREFIX-001 (3 digits)
    return f"{prefix}-{new_number:03d}"


# ==================== UNIT STAFF ROUTES ====================

@bp.route('/')
@login_required
@role_required('unit_staff')
def index():
    """List all procurement requests for the unit"""
    status_filter = request.args.get('status', '')

    # Get user's unit
    user_unit = current_user.units.first()
    if not user_unit:
        flash('Anda belum ditugaskan ke unit manapun!', 'warning')
        return redirect(url_for('main.index'))

    query = UnitProcurement.query.filter_by(unit_id=user_unit.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    procurements = query.order_by(UnitProcurement.created_at.desc()).all()

    # Get statistics
    total_procurements = UnitProcurement.query.filter_by(unit_id=user_unit.id).count()
    pending_count = UnitProcurement.query.filter_by(unit_id=user_unit.id, status='pending_verification').count()
    verified_count = UnitProcurement.query.filter_by(unit_id=user_unit.id, status='verified').count()
    in_procurement_count = UnitProcurement.query.filter_by(unit_id=user_unit.id, status='in_procurement').count()
    received_count = UnitProcurement.query.filter_by(unit_id=user_unit.id, status='received').count()
    completed_count = UnitProcurement.query.filter_by(unit_id=user_unit.id, status='completed').count()

    return render_template('unit_procurement/index.html',
                         procurements=procurements,
                         unit=user_unit,
                         stats={
                             'total': total_procurements,
                             'pending': pending_count,
                             'verified': verified_count,
                             'in_procurement': in_procurement_count,
                             'received': received_count,
                             'completed': completed_count
                         },
                         current_filter=status_filter)


@bp.route('/request', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def create_request():
    """Unit staff creates procurement request with multiple items"""
    form = UnitProcurementRequestForm()

    # Get user's unit
    user_unit = current_user.units.first()
    if not user_unit:
        flash('Anda belum ditugaskan ke unit manapun!', 'warning')
        return redirect(url_for('unit_procurement.index'))

    if request.method == 'POST':
        try:
            # Get items data from form
            items_data = request.form.getlist('items')
            request_notes = form.request_notes.data

            if not items_data or len(items_data) == 0:
                flash('Minimal harus ada satu barang yang diminta!', 'danger')
                return render_template('unit_procurement/request.html',
                                     form=form,
                                     unit=user_unit)

            # Validate and process items (same logic as warehouse procurement)
            valid_items = []
            for item_json in items_data:
                import json
                item_data = json.loads(item_json)

                # Check if user selected existing item or new item
                if item_data.get('item_id') == -1:
                    # Barang baru - langsung buat item baru di tabel items
                    if not item_data.get('item_name'):
                        flash('Nama barang baru harus diisi!', 'danger')
                        return render_template('unit_procurement/request.html',
                                             form=form,
                                             unit=user_unit)

                    if not item_data.get('item_category_id') or item_data.get('item_category_id') == 0:
                        flash('Kategori barang harus dipilih!', 'danger')
                        return render_template('unit_procurement/request.html',
                                             form=form,
                                             unit=user_unit)

                    # Buat item baru langsung di tabel items
                    # Generate item code based on category
                    item_code = generate_item_code(item_data.get('item_category_id'))

                    new_item = Item(
                        name=item_data.get('item_name'),
                        item_code=item_code,
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
                        return render_template('unit_procurement/request.html',
                                             form=form,
                                             unit=user_unit)

                    valid_items.append({
                        'item_id': item_data.get('item_id'),
                        'quantity': item_data.get('quantity'),
                        'is_new_item': False
                    })

            if not valid_items:
                flash('Tidak ada barang valid yang diminta!', 'danger')
                return render_template('unit_procurement/request.html',
                                     form=form,
                                     unit=user_unit)

            # Create unit procurement
            unit_procurement = UnitProcurement(
                unit_id=user_unit.id,
                request_notes=request_notes,
                status='pending_verification',
                requested_by=current_user.id,
                request_date=datetime.now()
            )
            unit_procurement.save()

            # Create unit procurement items
            for item_data in valid_items:
                unit_procurement_item = UnitProcurementItem(
                    unit_procurement_id=unit_procurement.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity']
                )
                unit_procurement_item.save()

            item_count = len(valid_items)
            flash(f'Permohonan pengadaan berhasil dibuat dengan {item_count} barang! Menunggu verifikasi admin.', 'success')

            return redirect(url_for('unit_procurement.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - prepare data for template
    items = Item.query.all()
    categories = Category.query.all()

    return render_template('unit_procurement/request.html',
                         form=form,
                         items=items,
                         categories=categories,
                         unit=user_unit)


@bp.route('/<int:id>')
@login_required
@role_required('unit_staff')
def detail(id):
    """View procurement request detail (for unit staff)"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Check if user belongs to this unit
    user_unit = current_user.units.first()
    if not user_unit or procurement.unit_id != user_unit.id:
        flash('Anda tidak memiliki akses ke permohonan ini!', 'danger')
        return redirect(url_for('unit_procurement.index'))

    # Update status from linked procurement if exists
    if procurement.procurement:
        procurement.update_status_from_procurement()

    return render_template('unit_procurement/detail.html', procurement=procurement)


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('unit_staff')
def cancel(id):
    """Cancel procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Check if user belongs to this unit
    user_unit = current_user.units.first()
    if not user_unit or procurement.unit_id != user_unit.id:
        flash('Anda tidak memiliki akses ke permohonan ini!', 'danger')
        return redirect(url_for('unit_procurement.index'))

    success, message = procurement.cancel(current_user.id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('unit_procurement.detail', id=id))


# ==================== ADMIN ROUTES ====================

@bp.route('/admin')
@login_required
@role_required('admin')
def admin_index():
    """List all unit procurement requests for admin verification"""
    status_filter = request.args.get('status', '')
    unit_filter = request.args.get('unit', '')

    query = UnitProcurement.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if unit_filter:
        query = query.filter_by(unit_id=unit_filter)

    procurements = query.order_by(UnitProcurement.created_at.desc()).all()

    # Get statistics
    total_procurements = UnitProcurement.query.count()
    pending_verification_count = UnitProcurement.query.filter_by(status='pending_verification').count()
    verified_count = UnitProcurement.query.filter_by(status='verified').count()
    approved_count = UnitProcurement.query.filter_by(status='approved').count()
    in_procurement_count = UnitProcurement.query.filter_by(status='in_procurement').count()
    received_count = UnitProcurement.query.filter_by(status='received').count()
    completed_count = UnitProcurement.query.filter_by(status='completed').count()

    units = Unit.query.all()

    return render_template('unit_procurement/admin_index.html',
                         procurements=procurements,
                         units=units,
                         stats={
                             'total': total_procurements,
                             'pending_verification': pending_verification_count,
                             'verified': verified_count,
                             'approved': approved_count,
                             'in_procurement': in_procurement_count,
                             'received': received_count,
                             'completed': completed_count
                         },
                         current_filter=status_filter,
                         current_unit=unit_filter)


@bp.route('/admin/<int:id>')
@login_required
@role_required('admin')
def admin_detail(id):
    """View procurement request detail (for admin)"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Update status from linked procurement if exists
    if procurement.procurement:
        procurement.update_status_from_procurement()

    return render_template('unit_procurement/admin_detail.html', procurement=procurement)


@bp.route('/admin/<int:id>/verify', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def verify(id):
    """Admin verifies unit procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status != 'pending_verification':
        flash('Hanya permohonan dengan status pending_verification yang bisa diverifikasi.', 'warning')
        return redirect(url_for('unit_procurement.admin_detail', id=id))

    form = UnitProcurementVerifyForm()

    if form.validate_on_submit():
        try:
            success, message = procurement.verify(
                user_id=current_user.id,
                notes=form.verification_notes.data
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('unit_procurement.admin_detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('unit_procurement/verify.html', procurement=procurement, form=form)


@bp.route('/admin/<int:id>/approve', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def approve(id):
    """Admin approves verified request and creates warehouse procurement"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status != 'verified':
        flash('Hanya permohonan yang sudah diverifikasi yang bisa disetujui.', 'warning')
        return redirect(url_for('unit_procurement.admin_detail', id=id))

    form = UnitProcurementApproveForm()
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]

    if form.validate_on_submit():
        try:
            success, message = procurement.approve(user_id=current_user.id)

            if success:
                # Add admin notes
                if form.admin_notes.data:
                    procurement.admin_notes = form.admin_notes.data

                # Set supplier to the linked warehouse procurement
                if procurement.procurement:
                    procurement.procurement.supplier_id = form.supplier_id.data
                    procurement.procurement.save()

                procurement.save()

                flash(f'{message} Supplier telah dipilih.', 'success')
                return redirect(url_for('unit_procurement.admin_detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('unit_procurement/approve.html', procurement=procurement, form=form)


@bp.route('/admin/<int:id>/reject', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def reject(id):
    """Admin rejects unit procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status in ['completed', 'in_procurement']:
        flash('Tidak bisa menolak permohonan yang sedang diproses atau sudah selesai.', 'warning')
        return redirect(url_for('unit_procurement.admin_detail', id=id))

    form = UnitProcurementRejectForm()

    if form.validate_on_submit():
        try:
            success, message = procurement.reject(
                user_id=current_user.id,
                reason=form.rejection_reason.data
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('unit_procurement.admin_detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('unit_procurement/reject.html', procurement=procurement, form=form)


@bp.route('/admin/<int:id>/procurement')
@login_required
@role_required('admin')
def view_linked_procurement(id):
    """View the linked warehouse procurement"""
    unit_procurement = UnitProcurement.query.get_or_404(id)

    if not unit_procurement.procurement:
        flash('Permohonan ini belum memiliki pengadaan yang terkait.', 'warning')
        return redirect(url_for('unit_procurement.admin_detail', id=id))

    return redirect(url_for('procurement.detail', id=unit_procurement.procurement_id))
