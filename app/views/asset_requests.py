from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AssetRequest, AssetRequestItem, Item, Unit, UnitDetail, User
from app.forms import AssetRequestForm, AssetVerificationForm
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('asset_requests', __name__, url_prefix='/asset-requests')


@bp.route('/')
@login_required
@role_required('unit_staff', 'admin')
def index():
    """List all asset requests"""
    from app.models import UserUnit

    status_filter = request.args.get('status', '')

    # Filter based on role
    if current_user.is_unit_staff():
        # Unit staff can only see requests for their units
        user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
        if not user_units:
            flash('Anda belum terassign ke unit manapun.', 'danger')
            return redirect(url_for('dashboard.index'))

        # Get unit IDs from user_units
        unit_ids = [uu.unit_id for uu in user_units]
        query = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids))
    else:  # admin
        query = AssetRequest.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    asset_requests = query.order_by(AssetRequest.created_at.desc()).all()

    # Convert to list to avoid len() error
    asset_requests_list = list(asset_requests)

    # Get statistics
    if current_user.is_unit_staff():
        total_requests = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids)).count()
        pending_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'pending').count()
        verified_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'verified').count()
        completed_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'completed').count()
    else:
        total_requests = AssetRequest.query.count()
        pending_count = AssetRequest.query.filter_by(status='pending').count()
        verified_count = AssetRequest.query.filter_by(status='verified').count()
        completed_count = AssetRequest.query.filter_by(status='completed').count()

    return render_template('asset_requests/index.html',
                         asset_requests=asset_requests_list,
                         stats={
                             'total': total_requests,
                             'pending': pending_count,
                             'verified': verified_count,
                             'completed': completed_count,
                             'rejected': 0  # Will calculate if needed
                         },
                         current_filter=status_filter)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def create():
    """Create new asset request"""
    from app.models import UserUnit

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('asset_requests.index'))

    # For now, just use the first assigned unit
    # TODO: Allow user to select which unit to request for
    user_unit = user_units[0]

    form = AssetRequestForm()

    if request.method == 'POST':
        try:
            # Get items data from form
            items_data = request.form.getlist('items')
            request_notes = form.request_notes.data

            if not items_data or len(items_data) == 0:
                flash('Minimal harus ada satu aset yang diminta!', 'danger')
                return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

            # Validate and process items
            import json
            valid_items = []
            for item_json in items_data:
                item_data = json.loads(item_json)

                # Validate
                if not item_data.get('item_id') or item_data.get('item_id') == 0:
                    flash('Harap pilih aset dari daftar!', 'danger')
                    return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

                quantity = item_data.get('quantity')
                if not quantity or quantity <= 0:
                    flash('Harap isi jumlah aset dengan benar!', 'danger')
                    return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

                valid_items.append({
                    'item_id': item_data.get('item_id'),
                    'quantity': quantity,
                    'unit_detail_id': item_data.get('unit_detail_id'),
                    'room_notes': item_data.get('room_notes', '')
                })

            # Create asset request
            asset_request = AssetRequest(
                unit_id=user_unit.unit_id,
                requested_by=current_user.id,
                request_date=datetime.now(),
                request_notes=request_notes,
                status='pending'
            )
            asset_request.save()

            # Create asset request items
            for item_data in valid_items:
                asset_request_item = AssetRequestItem(
                    asset_request_id=asset_request.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity'],
                    unit_detail_id=item_data.get('unit_detail_id'),
                    room_notes=item_data.get('room_notes', '')
                )
                asset_request_item.save()

            item_count = len(valid_items)
            flash(f'Permohonan aset berhasil dibuat dengan {item_count} aset! Menunggu verifikasi admin.', 'success')

            return redirect(url_for('asset_requests.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - prepare data
    items = Item.query.all()
    unit_details = UnitDetail.query.filter_by(unit_id=user_unit.unit_id).all()

    return render_template('asset_requests/create.html',
                         form=form,
                         items=items,
                         unit_details=unit_details,
                         unit=user_unit.unit)


@bp.route('/<int:id>')
@login_required
@role_required('unit_staff', 'admin')
def detail(id):
    """Show asset request details"""
    asset_request = AssetRequest.query.get_or_404(id)

    # Check permission
    if current_user.is_unit_staff():
        from app.models import UserUnit
        user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
        unit_ids = [uu.unit_id for uu in user_units]
        if asset_request.unit_id not in unit_ids:
            flash('Anda tidak memiliki izin untuk melihat permohonan ini.', 'danger')
            return redirect(url_for('asset_requests.index'))

    return render_template('asset_requests/detail.html', asset_request=asset_request)


@bp.route('/<int:id>/verify', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def verify(id):
    """Verify asset request (admin only)"""
    asset_request = AssetRequest.query.get_or_404(id)

    if asset_request.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa diverifikasi.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    form = AssetVerificationForm()

    if form.validate_on_submit():
        try:
            success, message = asset_request.verify(
                user_id=current_user.id,
                notes=form.notes.data
            )

            if success:
                flash(f'{message} Permohonan siap diproses.', 'success')
                return redirect(url_for('asset_requests.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_requests/verify.html', asset_request=asset_request, form=form)


@bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject(id):
    """Reject asset request (admin only)"""
    asset_request = AssetRequest.query.get_or_404(id)

    if asset_request.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa ditolak.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    rejection_reason = request.form.get('rejection_reason', '')

    try:
        success, message = asset_request.reject(
            user_id=current_user.id,
            reason=rejection_reason
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('asset_requests.detail', id=id))


@bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@role_required('unit_staff')
def complete(id):
    """Mark asset request as completed after receiving items"""
    asset_request = AssetRequest.query.get_or_404(id)

    if asset_request.status != 'verified':
        flash('Hanya permohonan yang sudah diverifikasi yang bisa diselesaikan.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    distribution_id = request.form.get('distribution_id', type=int)

    if not distribution_id:
        flash('Distribution ID diperlukan.', 'danger')
        return redirect(url_for('asset_requests.detail', id=id))

    try:
        success, message = asset_request.mark_completed(
            distribution_id=distribution_id,
            user_id=current_user.id
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('asset_requests.detail', id=id))


@bp.route('/unit-assets')
@login_required
@role_required('unit_staff')
def unit_assets():
    """Show all assets in the unit staff's units"""
    from app.models import UserUnit
    from app.models.distribution import Distribution

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get all unit IDs
    unit_ids = [uu.unit_id for uu in user_units]

    # Get all distributions to these units that are completed
    distributions = Distribution.query.filter(
        Distribution.unit_id.in_(unit_ids),
        Distribution.status == 'completed'
    ).all()

    # Collect all items from distributions
    unit_items = []
    for dist in distributions:
        if dist.item:
            unit_items.append({
                'item': dist.item,
                'quantity': dist.quantity,
                'distribution_date': dist.created_at,
                'location': f"{dist.unit.name} - {dist.unit_detail.room_name if dist.unit_detail else 'N/A'}"
            })

    # Get all units for display
    units = [uu.unit for uu in user_units]

    return render_template('asset_requests/unit_assets.html',
                         units=units,
                         unit_items=unit_items)
