from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Distribution, ItemDetail, User, Unit, UnitDetail, AssetRequest, AssetRequestItem
from app.forms import DistributionForm, InstallationForm
from app.utils.decorators import role_required, warehouse_access_required
from app.utils.datetime_helper import get_wib_now

bp = Blueprint('installations', __name__, url_prefix='/installations')


@bp.route('/')
@login_required
@warehouse_access_required
def index():
    """List all installations"""
    from sqlalchemy import or_

    # Get task type filter from URL parameter
    task_type_filter = request.args.get('task_type', '')  # 'installation' or 'delivery' or empty for all

    if current_user.is_warehouse_staff():
        # Filter installations by task type if specified
        installations_query = Distribution.query.filter_by(warehouse_id=current_user.warehouse_id)
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)
        installations = installations_query.all()

        # Get unique units and field staffs for filters
        units = Unit.query.join(Distribution).filter(Distribution.warehouse_id == current_user.warehouse_id).distinct().all()
        field_staffs = User.query.join(Distribution, User.id == Distribution.field_staff_id).filter(Distribution.warehouse_id == current_user.warehouse_id, User.role == 'field_staff').distinct().all()
    elif current_user.is_field_staff():
        # Filter installations by task type if specified
        installations_query = Distribution.query.filter_by(field_staff_id=current_user.id)
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)
        installations = installations_query.all()

        units = []
        field_staffs = []
    else:  # admin
        # Filter installations by task type if specified
        installations_query = Distribution.query
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)
        installations = installations_query.all()

        units = Unit.query.join(Distribution).distinct().all()
        field_staffs = User.query.filter_by(role='field_staff').all()

    return render_template('installations/index.html',
                         distributions=installations,
                         units=units,
                         field_staffs=field_staffs,
                         task_type_filter=task_type_filter)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def create():
    """Create new installation request"""
    form = InstallationForm()

    # Populate form choices
    if current_user.is_warehouse_staff():
        # Only show available items in this warehouse
        available_items = ItemDetail.query.filter_by(
            warehouse_id=current_user.warehouse_id,
            status='available'
        ).all()
        form.item_detail_id.choices = [(i.id, f"{i.item.name} - {i.serial_number}") for i in available_items]
    else:
        available_items = ItemDetail.query.filter_by(status='available').all()
        form.item_detail_id.choices = [(i.id, f"{i.item.name} - {i.serial_number}") for i in available_items]

    form.field_staff_id.choices = [(u.id, u.name) for u in User.query.filter_by(role='field_staff').all()]
    form.unit_id.choices = [(u.id, u.name) for u in Unit.query.all()]

    # Dynamically load unit details based on selected unit
    selected_unit_id = request.args.get('unit_id', type=int)
    if selected_unit_id:
        form.unit_detail_id.choices = [(ud.id, ud.room_name) for ud in UnitDetail.query.filter_by(unit_id=selected_unit_id).all()]
    else:
        form.unit_detail_id.choices = []

    if form.validate_on_submit():
        try:
            # Get item detail
            item_detail = ItemDetail.query.get(form.item_detail_id.data)

            # Create distribution
            distribution = Distribution(
                item_detail_id=form.item_detail_id.data,
                warehouse_id=item_detail.warehouse_id,
                field_staff_id=form.field_staff_id.data,
                unit_id=form.unit_id.data,
                unit_detail_id=form.unit_detail_id.data,
                address=form.address.data,
                note=form.note.data,
                status='installing'
            )

            # Set coordinates if provided
            if form.latitude.data and form.longitude.data:
                distribution.set_coordinates(form.latitude.data, form.longitude.data)

            distribution.save()

            # Update item status
            item_detail.status = 'processing'
            item_detail.save()

            # Log the movement
            from app.models import AssetMovementLog
            from app.utils import send_notification

            AssetMovementLog.log_movement(
                item_detail=item_detail,
                operator=current_user,
                origin_type='warehouse',
                origin_id=item_detail.warehouse_id,
                destination_type='unit',
                destination_id=form.unit_id.data,
                status_before='available',
                status_after='processing',
                note=f"Installation request created: {form.note.data}"
            )

            # Send notification to field staff
            field_staff = User.query.get(form.field_staff_id.data)
            send_notification(field_staff, f"Anda mendapat tugas instalasi baru: {item_detail.item.name} - {item_detail.serial_number}")

            flash('Permintaan instalasi berhasil dibuat!', 'success')
            return redirect(url_for('installations.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('installations/create.html', form=form)


@bp.route('/<int:id>/verify', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def verify(id):
    """Verify installation completion (legacy - direct verify)"""
    distribution = Distribution.query.get_or_404(id)

    try:
        # Update distribution status
        distribution.status = 'installed'
        distribution.save()

        # Update item detail status
        item_detail = distribution.item_detail
        item_detail.status = 'used'
        item_detail.save()

        # Log the movement
        from app.models import AssetMovementLog

        AssetMovementLog.log_movement(
            item_detail=item_detail,
            operator=current_user,
            origin_type='warehouse',
            origin_id=distribution.warehouse_id,
            destination_type='unit',
            destination_id=distribution.unit_id,
            status_before='processing',
            status_after='used',
            note='Installation verified and completed'
        )

        flash('Instalasi berhasil diverifikasi!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('installations.index'))


@bp.route('/<int:id>/verify-task', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def verify_task(id):
    """Verify task completion from field staff with photo verification"""
    distribution = Distribution.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and distribution.warehouse_id != current_user.warehouse_id:
        flash('Anda tidak memiliki akses ke tugas ini.', 'danger')
        return redirect(url_for('installations.index'))

    if request.method == 'POST':
        action = request.form.get('action')  # 'approve' or 'reject'
        rejection_reason = request.form.get('rejection_reason', '')

        try:
            if action == 'approve':
                success, message = distribution.verify_task(current_user.id)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'danger')
            elif action == 'reject':
                if not rejection_reason:
                    flash('Mohon isi alasan penolakan.', 'warning')
                    return render_template('installations/verify_task.html', distribution=distribution)
                success, message = distribution.reject_verification(current_user.id, rejection_reason)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'danger')
            return redirect(url_for('installations.verify_task', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('installations/verify_task.html', distribution=distribution)


@bp.route('/<int:id>/detail')
@login_required
def detail(id):
    """View installation detail"""
    installation = Distribution.query.get_or_404(id)
    return render_template('installations/detail.html', installation=installation)


@bp.route('/<int:id>/update/<string:status>', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def update_status(id, status):
    """Update distribution status"""
    distribution = Distribution.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and distribution.warehouse_id != current_user.warehouse_id:
        flash('Anda tidak memiliki akses ke tugas ini.', 'danger')
        return redirect(url_for('installations.index'))

    # Valid status values
    valid_statuses = ['installing', 'in_transit', 'installed', 'broken', 'maintenance']
    if status not in valid_statuses:
        flash('Status tidak valid.', 'danger')
        return redirect(url_for('installations.detail', id=id))

    try:
        distribution.status = status
        distribution.save()

        # If status is installed, update item detail status
        if status == 'installed':
            if distribution.item_detail:
                distribution.item_detail.status = 'used'
                distribution.item_detail.save()

        flash(f'Status berhasil diperbarui menjadi {distribution.status_display}.', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('installations.detail', id=id))


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def cancel(id):
    """Cancel installation"""
    distribution = Distribution.query.get_or_404(id)

    try:
        # Revert item status
        item_detail = distribution.item_detail
        item_detail.status = 'available'
        item_detail.save()

        # Delete distribution
        distribution.delete()

        flash('Instalasi berhasil dibatalkan.', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('installations.index'))


@bp.route('/asset-request/<int:request_id>/distribute', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def distribute_asset_request(request_id):
    """Process verified asset request and create distributions"""
    from app.models import User
    asset_request = AssetRequest.query.get_or_404(request_id)

    if asset_request.status != 'verified':
        flash('Hanya permohonan yang sudah diverifikasi yang dapat diproses.', 'warning')
        return redirect(url_for('installations.index'))

    if asset_request.distribution_id:
        flash('Permohonan ini sudah memiliki distribusi.', 'info')
        return redirect(url_for('installations.index'))

    if request.method == 'POST':
        try:
            # Get available field staff
            field_staffs = User.query.filter_by(role='field_staff').all()

            if not field_staffs:
                flash('Tidak ada field staff tersedia. Silakan tambahkan field staff terlebih dahulu.', 'danger')
                return redirect(url_for('installations.index'))

            # For each item in the asset request, create distribution
            request_items = AssetRequestItem.query.filter_by(asset_request_id=request_id).all()

            if not request_items:
                flash('Tidak ada item dalam permohonan ini.', 'danger')
                return redirect(url_for('installations.index'))

            distributions_created = []
            distribution_data = []

            for req_item in request_items:
                # Determine if this is networking item
                is_networking = req_item.item.category.name.lower() in ['networking', 'jaringan']
                task_type = 'installation' if is_networking else 'delivery'

                # Find available item details in warehouse that don't already have a distribution
                # Subquery to get item_detail_ids that already have distributions
                from sqlalchemy import distinct
                existing_distribution_item_ids = db.session.query(
                    Distribution.item_detail_id
                ).filter(
                    Distribution.item_detail_id.isnot(None)
                ).all()
                existing_ids = [item_id[0] for item_id in existing_distribution_item_ids]

                # Find available items excluding those already distributed
                available_items = ItemDetail.query.filter(
                    ItemDetail.item_id == req_item.item_id,
                    ItemDetail.status == 'available',
                    ~ItemDetail.id.in_(existing_ids)
                ).limit(req_item.quantity).all()

                if len(available_items) < req_item.quantity:
                    flash(f'Stok tidak mencukupi untuk {req_item.item.name}. Tersedia: {len(available_items)}, Diminta: {req_item.quantity}', 'danger')
                    return redirect(url_for('installations.index'))

                # Assign field staff (round-robin or first available)
                # For simplicity, assign to first field staff
                field_staff = field_staffs[0]

                # Create distribution for each item detail
                for item_detail in available_items:
                    # Use helper function to create distribution
                    distribution = Distribution.create_from_asset_request_item(
                        asset_request_item=req_item,
                        warehouse_id=item_detail.warehouse_id,
                        field_staff_id=field_staff.id,
                        item_detail_id=item_detail.id
                    )

                    # Update task type based on category
                    distribution.task_type = task_type
                    if task_type == 'delivery':
                        distribution.status = 'in_transit'
                    distribution.save()

                    distributions_created.append(distribution)

            # Link asset request to first distribution
            if distributions_created:
                asset_request.distribution_id = distributions_created[0].id
                asset_request.status = 'distributing'
                asset_request.distributed_by = current_user.id
                asset_request.distributed_at = get_wib_now()
                asset_request.save()

            print(f"=== DEBUG DISTRIBUTION CREATED ===")
            print(f"Created {len(distributions_created)} distributions")
            for dist in distributions_created:
                print(f"  - Distribution ID: {dist.id}, Item: {dist.item_detail.item.name if dist.item_detail else 'N/A'}, Field Staff ID: {dist.field_staff_id}, Warehouse ID: {dist.warehouse_id}")
            print(f"Current warehouse staff warehouse_id: {current_user.warehouse_id}")
            print(f"=================================")

            flash(f'Berhasil membuat {len(distributions_created)} distribusi untuk permohonan aset #{asset_request.id}! Field staff akan menerima task.', 'success')
            return redirect(url_for('installations.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show confirmation
    return render_template('installations/distribute_asset_request.html', asset_request=asset_request)
