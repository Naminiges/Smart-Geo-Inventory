import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.models import AssetLoan, AssetLoanItem, Item, ItemDetail, Unit, Warehouse, User
from app.forms import (
    AssetLoanRequestForm,
    AssetLoanApproveForm,
    AssetLoanShipForm,
    AssetLoanReceiveForm,
    AssetLoanReturnRequestForm,
    AssetLoanReturnApproveForm,
    AssetLoanItemReturnVerifyForm,
    AssetLoanItemUploadProofForm
)
from app.utils.decorators import role_required
from app.utils.helpers import get_user_warehouse_id

bp = Blueprint('asset_loans', __name__, url_prefix='/asset-loans')


def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif'}):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# ==================== UNIT STAFF VIEWS ====================

@bp.route('/unit')
@login_required
@role_required('unit_staff')
def unit_index():
    """List all venue loans for unit staff (Venue/Room borrowing)"""
    from app.models import VenueLoan

    # Get units assigned to this user
    user_units = current_user.get_assigned_units()

    if not user_units:
        flash('Anda belum ditugaskan ke unit manapun.', 'warning')
        return redirect(url_for('dashboard.index'))

    # Get unit IDs
    unit_ids = [unit.id for unit in user_units]

    # Get venue loans for these units (as borrower)
    venue_loans = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids)
    ).order_by(VenueLoan.created_at.desc()).all()

    # Get statistics
    total_count = VenueLoan.query.filter(VenueLoan.borrower_unit_id.in_(unit_ids)).count()
    pending_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'pending'
    ).count()
    active_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'active'
    ).count()
    approved_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'approved'
    ).count()

    return render_template('asset_loans/unit/index.html',
                         venue_loans=venue_loans,
                         stats={
                             'total': total_count,
                             'pending': pending_count,
                             'active': active_count,
                             'approved': approved_count
                         })


@bp.route('/unit/request', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def unit_request():
    """Create new asset loan request (Unit staff)"""
    form = AssetLoanRequestForm()

    # Get units assigned to this user
    user_units = current_user.get_assigned_units()

    if not user_units:
        flash('Anda belum ditugaskan ke unit manapun.', 'warning')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        try:
            # Get items data from form
            items_data = request.form.getlist('items')
            request_notes = form.request_notes.data

            # Get selected unit from form
            selected_unit_id = request.form.get('unit_id')
            if not selected_unit_id:
                flash('Harap pilih unit!', 'danger')
                return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

            # Verify user has access to this unit
            selected_unit_id = int(selected_unit_id)
            if not any(unit.id == selected_unit_id for unit in user_units):
                flash('Anda tidak memiliki akses ke unit ini.', 'danger')
                return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

            if not items_data or len(items_data) == 0:
                flash('Minimal harus ada satu barang yang diminta!', 'danger')
                return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

            # Validate and process items
            valid_items = []
            for item_json in items_data:
                item_data = json.loads(item_json)

                # Check if user selected existing item detail
                if not item_data.get('item_detail_id') or item_data.get('item_detail_id') == 0:
                    flash('Harap pilih barang dari daftar!', 'danger')
                    return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

                valid_items.append({
                    'item_detail_id': item_data.get('item_detail_id'),
                    'quantity': item_data.get('quantity', 1)
                })

            if not valid_items:
                flash('Tidak ada barang valid yang diminta!', 'danger')
                return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

            # Get warehouse for this unit (default to first warehouse)
            warehouse = Warehouse.query.first()
            if not warehouse:
                flash('Warehouse belum tersedia. Hubungi admin.', 'danger')
                return render_template('asset_loans/unit/request.html', form=form, user_units=user_units, available_items=get_available_items())

            # Create asset loan
            asset_loan = AssetLoan(
                unit_id=selected_unit_id,
                warehouse_id=warehouse.id,
                request_notes=request_notes,
                status='pending',
                requested_by=current_user.id,
                request_date=datetime.now()
            )
            asset_loan.save()

            # Create asset loan items
            for item_data in valid_items:
                loan_item = AssetLoanItem(
                    asset_loan_id=asset_loan.id,
                    item_detail_id=item_data['item_detail_id'],
                    quantity=item_data['quantity']
                )
                loan_item.save()

            item_count = len(valid_items)
            flash(f'Permohonan peminjaman berhasil dibuat dengan {item_count} barang! Menunggu persetujuan warehouse.', 'success')

            return redirect(url_for('asset_loans.unit_index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - prepare data for template
    return render_template('asset_loans/unit/request.html',
                         form=form,
                         user_units=user_units,
                         available_items=get_available_items())


def get_available_items():
    """Helper function to get available non-networking items"""
    from app.models import Category

    # Get all available items that are NOT networking-related
    available_items = ItemDetail.query.filter_by(status='available').join(Item).join(
        Category
    ).filter(
        ~Category.name.ilike('%jaringan%'),
        ~Category.name.ilike('%networking%')
    ).all()

    return available_items


@bp.route('/unit/<int:id>/receive', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def unit_receive(id):
    """Unit staff confirms receipt of loaned items"""
    loan = AssetLoan.query.get_or_404(id)

    # Check if user has access to this loan's unit
    user_unit_ids = [unit.id for unit in current_user.get_assigned_units()]
    if loan.unit_id not in user_unit_ids:
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.unit_index'))

    if loan.status != 'shipped':
        flash('Hanya peminjaman dengan status shipped yang bisa diterima.', 'warning')
        return redirect(url_for('asset_loans.unit_detail', id=id))

    form = AssetLoanReceiveForm()

    if form.validate_on_submit():
        try:
            success, message = loan.receive_by_unit(current_user.id, form.receipt_notes.data)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.unit_detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/unit/receive.html', loan=loan, form=form)


@bp.route('/unit/<int:id>/detail')
@login_required
@role_required('unit_staff')
def unit_detail(id):
    """View asset loan detail (Unit staff)"""
    loan = AssetLoan.query.get_or_404(id)

    # Check if user has access to this loan's unit
    user_unit_ids = [unit.id for unit in current_user.get_assigned_units()]
    if loan.unit_id not in user_unit_ids:
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.unit_index'))

    return render_template('asset_loans/unit/detail.html', loan=loan)


@bp.route('/unit/<int:id>/request-return', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def unit_request_return(id):
    """Unit staff requests return of loaned items"""
    loan = AssetLoan.query.get_or_404(id)

    # Check if user has access to this loan's unit
    user_unit_ids = [unit.id for unit in current_user.get_assigned_units()]
    if loan.unit_id not in user_unit_ids:
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.unit_index'))

    if loan.status != 'active':
        flash('Hanya peminjaman aktif yang bisa diajukan retur.', 'warning')
        return redirect(url_for('asset_loans.unit_detail', id=id))

    form = AssetLoanReturnRequestForm()

    if form.validate_on_submit():
        try:
            success, message = loan.request_return(current_user.id, form.return_reason.data)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.unit_detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/unit/request_return.html', loan=loan, form=form)


@bp.route('/unit/item/<int:item_id>/upload-proof', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def unit_upload_return_proof(item_id):
    """Unit staff uploads return proof photo for individual item"""
    loan_item = AssetLoanItem.query.get_or_404(item_id)
    loan = loan_item.asset_loan

    # Check if user has access to this loan's unit
    user_unit_ids = [unit.id for unit in current_user.get_assigned_units()]
    if loan.unit_id not in user_unit_ids:
        flash('Anda tidak memiliki akses ke item ini.', 'danger')
        return redirect(url_for('asset_loans.unit_index'))

    if loan.status != 'returned':
        flash('Pengembalian belum disetujui warehouse.', 'warning')
        return redirect(url_for('asset_loans.unit_detail', id=loan.id))

    if loan_item.return_verification_status == 'verified':
        flash('Item sudah diverifikasi.', 'info')
        return redirect(url_for('asset_loans.unit_detail', id=loan.id))

    form = AssetLoanItemUploadProofForm()

    if form.validate_on_submit():
        try:
            # Handle file upload
            photo_path = None
            if 'return_photo' in request.files:
                file = request.files['return_photo']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'return_proofs')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    photo_path = f"/static/uploads/return_proofs/{filename}"

            # Update loan item
            loan_item.return_photo = photo_path
            loan_item.return_notes = form.return_notes.data
            loan_item.return_verification_status = 'submitted'
            loan_item.save()

            flash('Bukti pengembalian berhasil diupload. Menunggu verifikasi warehouse.', 'success')
            return redirect(url_for('asset_loans.unit_detail', id=loan.id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/unit/upload_proof.html', loan=loan, loan_item=loan_item, form=form)


# ==================== WAREHOUSE STAFF VIEWS ====================

@bp.route('/warehouse')
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_index():
    """List all asset loans for warehouse staff"""
    # Filter by warehouse if warehouse staff
    if current_user.is_warehouse_staff():
        loans = AssetLoan.query.filter_by(warehouse_id=get_user_warehouse_id(current_user)).order_by(AssetLoan.created_at.desc()).all()
    else:  # admin
        loans = AssetLoan.query.order_by(AssetLoan.created_at.desc()).all()

    # Get statistics
    total_loans = len(loans)
    pending_count = len([l for l in loans if l.status == 'pending'])
    approved_count = len([l for l in loans if l.status == 'approved'])
    shipped_count = len([l for l in loans if l.status == 'shipped'])
    active_count = len([l for l in loans if l.status == 'active'])
    returned_count = len([l for l in loans if l.status == 'returned'])

    return render_template('asset_loans/warehouse/index.html',
                         loans=loans,
                         stats={
                             'total': total_loans,
                             'pending': pending_count,
                             'approved': approved_count,
                             'shipped': shipped_count,
                             'active': active_count,
                             'returned': returned_count
                         })


@bp.route('/warehouse/<int:id>/detail')
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_detail(id):
    """View asset loan detail (Warehouse staff)"""
    loan = AssetLoan.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    return render_template('asset_loans/warehouse/detail.html', loan=loan)


@bp.route('/warehouse/<int:id>/approve', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_approve(id):
    """Warehouse staff approves loan request"""
    loan = AssetLoan.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    if loan.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa disetujui.', 'warning')
        return redirect(url_for('asset_loans.warehouse_detail', id=id))

    form = AssetLoanApproveForm()

    if form.validate_on_submit():
        try:
            success, message = loan.approve(current_user.id, form.approval_notes.data)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.warehouse_detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/warehouse/approve.html', loan=loan, form=form)


@bp.route('/warehouse/<int:id>/reject', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_reject(id):
    """Warehouse staff rejects loan request"""
    loan = AssetLoan.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    rejection_reason = request.form.get('rejection_reason', '')

    try:
        success, message = loan.reject(current_user.id, rejection_reason)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('asset_loans.warehouse_index'))


@bp.route('/warehouse/<int:id>/ship', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_ship(id):
    """Warehouse staff ships loaned items"""
    loan = AssetLoan.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    if loan.status != 'approved':
        flash('Hanya permohonan yang sudah disetujui yang bisa dikirim.', 'warning')
        return redirect(url_for('asset_loans.warehouse_detail', id=id))

    form = AssetLoanShipForm()

    if form.validate_on_submit():
        try:
            success, message = loan.ship(current_user.id, form.shipment_notes.data)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.warehouse_detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/warehouse/ship.html', loan=loan, form=form)


@bp.route('/warehouse/<int:id>/approve-return', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_approve_return(id):
    """Warehouse staff approves return request"""
    loan = AssetLoan.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke peminjaman ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    if loan.status != 'returned':
        flash('Tidak ada permohonan retur untuk disetujui.', 'warning')
        return redirect(url_for('asset_loans.warehouse_detail', id=id))

    form = AssetLoanReturnApproveForm()

    if form.validate_on_submit():
        try:
            success, message = loan.approve_return(current_user.id, form.return_notes.data)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.warehouse_detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/warehouse/approve_return.html', loan=loan, form=form)


@bp.route('/warehouse/item/<int:item_id>/verify-return', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_verify_return(item_id):
    """Warehouse staff verifies return of individual item"""
    loan_item = AssetLoanItem.query.get_or_404(item_id)
    loan = loan_item.asset_loan

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke item ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    if loan_item.return_verification_status not in ['submitted', 'pending']:
        flash('Item tidak dalam status menunggu verifikasi.', 'warning')
        return redirect(url_for('asset_loans.warehouse_detail', id=loan.id))

    form = AssetLoanItemReturnVerifyForm()

    if form.validate_on_submit():
        try:
            action = form.action.data
            approve = action == 'approve'
            reason = form.rejection_reason.data if not approve else None

            success, message = loan.verify_return_item(item_id, current_user.id, approve, reason)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('asset_loans.warehouse_detail', id=loan.id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_loans/warehouse/verify_return.html', loan=loan, loan_item=loan_item, form=form)


@bp.route('/warehouse/item/<int:item_id>/view-proof')
@login_required
@role_required('warehouse_staff', 'admin')
def warehouse_view_proof(item_id):
    """Warehouse staff views return proof photo"""
    loan_item = AssetLoanItem.query.get_or_404(item_id)
    loan = loan_item.asset_loan

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and loan.warehouse_id != get_user_warehouse_id(current_user):
        flash('Anda tidak memiliki akses ke item ini.', 'danger')
        return redirect(url_for('asset_loans.warehouse_index'))

    if not loan_item.return_photo:
        flash('Tidak ada foto bukti pengembalian.', 'warning')
        return redirect(url_for('asset_loans.warehouse_detail', id=loan.id))

    return render_template('asset_loans/warehouse/view_proof.html', loan=loan, loan_item=loan_item)
