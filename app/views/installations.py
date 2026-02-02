from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Distribution, ItemDetail, Item, User, Unit, UnitDetail, AssetRequest, AssetRequestItem, Warehouse
from app.forms import DistributionForm, InstallationForm
from app.utils.decorators import role_required, warehouse_access_required
from app.utils.datetime_helper import get_wib_now
from app.utils.helpers import get_user_warehouse_id
from app.services.notifications import (
    notify_distribution_created,
    notify_distribution_sent,
    notify_distribution_received,
    notify_distribution_rejected
)

bp = Blueprint('installations', __name__, url_prefix='/installations')


@bp.route('/drafts')
@login_required
@role_required('admin', 'warehouse_staff')
def draft_list():
    """List all draft distributions waiting for verification"""
    from datetime import timedelta

    # Get all draft distributions, newest first
    if current_user.is_admin():
        drafts = Distribution.query.filter_by(is_draft=True).order_by(Distribution.created_at.desc()).all()
    else:  # warehouse staff
        drafts = Distribution.query.filter_by(warehouse_id=get_user_warehouse_id(current_user), is_draft=True).order_by(Distribution.created_at.desc()).all()

    # Group drafts by batch for admin verification
    draft_batches = []
    if drafts:
        batch_dict = {}
        for draft in drafts:
            time_window = draft.created_at.replace(second=0, microsecond=0)
            batch_key = (draft.draft_created_by, draft.unit_id, draft.draft_notes, time_window)

            if batch_key not in batch_dict:
                batch_dict[batch_key] = []
            batch_dict[batch_key].append(draft)

        for batch_key, batch_drafts in batch_dict.items():
            creator_id, unit_id, notes, time_window = batch_key
            draft_batches.append({
                'drafts': batch_drafts,
                'creator': batch_drafts[0].draft_creator if batch_drafts[0].draft_creator else None,
                'unit': batch_drafts[0].unit if batch_drafts[0].unit else None,
                'notes': notes,
                'created_at': batch_drafts[0].created_at,
                'total_items': len(batch_drafts),
                'ref_id': batch_drafts[0].id
            })

        draft_batches.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('installations/draft_list.html', draft_batches=draft_batches)


@bp.route('/rejected')
@login_required
@role_required('admin', 'warehouse_staff')
def rejected_list():
    """List all rejected draft distributions from rejected_distributions table"""
    from app.models import RejectedDistribution, DistributionGroup

    # Get rejected distribution groups first
    if current_user.is_admin():
        # Admin sees all rejected groups
        rejected_groups = DistributionGroup.query.filter(
            DistributionGroup.status == 'rejected'
        ).order_by(DistributionGroup.rejected_at.desc()).all()
    else:  # warehouse staff
        # Warehouse staff sees rejected groups from their warehouse
        rejected_groups = DistributionGroup.query.filter(
            DistributionGroup.warehouse_id == get_user_warehouse_id(current_user),
            DistributionGroup.status == 'rejected'
        ).order_by(DistributionGroup.rejected_at.desc()).all()

    # Get rejected distributions that are not part of any group (old style, if any)
    if current_user.is_admin():
        orphan_rejected = RejectedDistribution.query.filter(
            RejectedDistribution.distribution_group_id == None
        ).order_by(RejectedDistribution.rejected_at.desc()).all()
    else:
        orphan_rejected = RejectedDistribution.query.filter(
            RejectedDistribution.warehouse_id == get_user_warehouse_id(current_user),
            RejectedDistribution.distribution_group_id == None
        ).order_by(RejectedDistribution.rejected_at.desc()).all()

    # Prepare rejected batches from groups
    rejected_batches = []

    # Process rejected groups
    for group in rejected_groups:
        # Get all rejected distributions for this group
        rejected_dist = RejectedDistribution.query.filter(
            RejectedDistribution.distribution_group_id == group.id
        ).all()

        if rejected_dist:
            rejected_batches.append({
                'drafts': rejected_dist,
                'creator': group.creator,
                'unit': group.unit,
                'notes': group.notes,
                'rejected_at': group.rejected_at,
                'rejector': group.rejector,
                'rejection_reason': group.rejection_reason,
                'total_items': len(rejected_dist),
                'ref_id': rejected_dist[0].id,
                'batch_code': group.batch_code,
                'is_group': True
            })

    # Process orphan rejected distributions (not part of any group)
    # Group them by time window
    if orphan_rejected:
        from collections import defaultdict
        from datetime import timedelta

        batch_dict = defaultdict(list)
        for rejected in orphan_rejected:
            # Group by creator, unit, notes, and time window (1 minute)
            time_window = rejected.rejected_at.replace(second=0, microsecond=0)
            batch_key = (rejected.draft_created_by, rejected.unit_id, rejected.draft_notes, time_window)
            batch_dict[batch_key].append(rejected)

        for batch_key, batch_items in batch_dict.items():
            creator_id, unit_id, notes, time_window = batch_key
            rejected_batches.append({
                'drafts': batch_items,
                'creator': batch_items[0].draft_creator,
                'unit': batch_items[0].unit,
                'notes': notes,
                'rejected_at': batch_items[0].rejected_at,
                'rejector': batch_items[0].rejector,
                'rejection_reason': batch_items[0].rejection_reason,
                'total_items': len(batch_items),
                'ref_id': batch_items[0].id,
                'batch_code': None,
                'is_group': False
            })

    # Sort by rejected_at
    rejected_batches.sort(key=lambda x: x['rejected_at'], reverse=True)

    return render_template('installations/rejected_list.html', rejected_batches=rejected_batches)


@bp.route('/')
@login_required
@warehouse_access_required
def index():
    """List all installations"""
    from sqlalchemy import or_
    from collections import defaultdict
    from datetime import timedelta

    # Get task type filter from URL parameter
    task_type_filter = request.args.get('task_type', '')  # 'installation' or 'delivery' or empty for all
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Initialize accessible_warehouse_ids for warehouse staff
    accessible_warehouse_ids = []

    if current_user.is_warehouse_staff():
        # Get all warehouse IDs this user has access to
        # Add direct warehouse_id if exists
        if get_user_warehouse_id(current_user):
            accessible_warehouse_ids.append(get_user_warehouse_id(current_user))

        # Add warehouses from user_warehouses assignments
        for uw in current_user.user_warehouses.all():
            if uw.warehouse_id not in accessible_warehouse_ids:
                accessible_warehouse_ids.append(uw.warehouse_id)

        # Filter installations: only direct distributions (not from asset requests) from accessible warehouses
        # Exclude rejected drafts and draft distributions
        installations_query = Distribution.query.filter(
            Distribution.warehouse_id.in_(accessible_warehouse_ids),
            Distribution.asset_request_id == None,
            Distribution.is_draft == False,
            Distribution.draft_rejected == False
        )
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)

        # Server-side pagination for installations
        pagination = installations_query.order_by(Distribution.draft_verified_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        installations = pagination.items

        # Get draft distributions from accessible warehouses only, newest first
        draft_query = Distribution.query.filter(
            Distribution.warehouse_id.in_(accessible_warehouse_ids),
            Distribution.is_draft == True
        )
        drafts = draft_query.order_by(Distribution.created_at.desc()).all()

        # Get unique units and field staffs for filters
        units = Unit.query.join(Distribution).filter(Distribution.warehouse_id.in_(accessible_warehouse_ids)).distinct().all()
        field_staffs = User.query.join(Distribution, User.id == Distribution.field_staff_id).filter(Distribution.warehouse_id.in_(accessible_warehouse_ids), User.role == 'field_staff').distinct().all()
    elif current_user.is_field_staff():
        # Filter installations by task type if specified
        # Exclude rejected drafts
        installations_query = Distribution.query.filter_by(field_staff_id=current_user.id).filter(
            Distribution.is_draft == False,
            Distribution.draft_rejected == False
        )
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)

        # Server-side pagination for installations
        pagination = installations_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        installations = pagination.items

        drafts = []  # Field staff doesn't see drafts
        units = []
        field_staffs = []
    else:  # admin
        # Filter installations: only direct distributions (not from asset requests), newest first
        # Exclude rejected drafts and draft distributions
        installations_query = Distribution.query.filter(
            Distribution.asset_request_id == None,
            Distribution.is_draft == False,
            Distribution.draft_rejected == False
        )
        if task_type_filter:
            installations_query = installations_query.filter_by(task_type=task_type_filter)

        # Server-side pagination for installations
        pagination = installations_query.order_by(Distribution.draft_verified_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        installations = pagination.items

        # Get all draft distributions, newest first
        drafts = Distribution.query.filter_by(is_draft=True).order_by(Distribution.created_at.desc()).all()

        units = Unit.query.join(Distribution).distinct().all()
        field_staffs = User.query.filter_by(role='field_staff').all()

    # Group active distributions by batch
    # A batch is defined by: created_by (draft_created_by for converted drafts, or field_staff_id),
    # unit_id, and created_at (within 1 minute)
    active_batches = []
    if installations:
        # Use a dict to track processed batches
        batch_dict = {}  # key: (creator_id, unit_id, time_window), value: list of distributions

        for dist in installations:
            # For warehouse staff, only show distributions from their accessible warehouses
            if current_user.is_warehouse_staff() and dist.warehouse_id not in accessible_warehouse_ids:
                continue

            # Determine who created this distribution (draft creator or field staff)
            creator_id = dist.draft_created_by if dist.draft_created_by else dist.field_staff_id

            # Calculate time window (floor to nearest minute)
            time_window = dist.created_at.replace(second=0, microsecond=0)
            batch_key = (creator_id, dist.unit_id, time_window)

            if batch_key not in batch_dict:
                batch_dict[batch_key] = []
            batch_dict[batch_key].append(dist)

        # Convert to list format for template
        for batch_key, batch_distributions in batch_dict.items():
            creator_id, unit_id, time_window = batch_key
            # Get creator (could be draft_creator or field_staff)
            creator = None
            if batch_distributions[0].draft_created_by:
                creator = batch_distributions[0].draft_creator
            elif batch_distributions[0].field_staff_id:
                creator = User.query.get(batch_distributions[0].field_staff_id)

            active_batches.append({
                'distributions': batch_distributions,
                'creator': creator,
                'unit': batch_distributions[0].unit if batch_distributions[0].unit else None,
                'created_at': batch_distributions[0].created_at,
                'verified_at': batch_distributions[0].draft_verified_at,  # Tambahkan verified_at
                'total_items': len(batch_distributions),
                'ref_id': batch_distributions[0].id,  # Use first distribution ID for detail link
                'statuses': list(set([d.status for d in batch_distributions]))  # Unique statuses in batch
            })

        # Sort by verified_at descending (waktu verifikasi admin)
        active_batches.sort(key=lambda x: (x['verified_at'] or datetime.min), reverse=True)

    # Group drafts by batch for admin/warehouse staff verification
    # A batch is defined by: draft_created_by, unit_id, draft_notes, and created_at (within 1 minute)
    draft_batches = []
    if drafts:
        # For warehouse staff, only show drafts from their accessible warehouses
        filtered_drafts = drafts
        if current_user.is_warehouse_staff():
            filtered_drafts = [d for d in drafts if d.warehouse_id in accessible_warehouse_ids]

        # Use a dict to track processed batches
        batch_dict = {}  # key: (creator_id, unit_id, notes, time_window), value: list of drafts

        for draft in filtered_drafts:
            # Calculate time window (floor to nearest minute)
            time_window = draft.created_at.replace(second=0, microsecond=0)
            batch_key = (draft.draft_created_by, draft.unit_id, draft.draft_notes, time_window)

            if batch_key not in batch_dict:
                batch_dict[batch_key] = []
            batch_dict[batch_key].append(draft)

        # Convert to list format for template
        for batch_key, batch_drafts in batch_dict.items():
            creator_id, unit_id, notes, time_window = batch_key
            draft_batches.append({
                'drafts': batch_drafts,
                'creator': batch_drafts[0].draft_creator if batch_drafts[0].draft_creator else None,
                'unit': batch_drafts[0].unit if batch_drafts[0].unit else None,
                'notes': notes,
                'created_at': batch_drafts[0].created_at,
                'total_items': len(batch_drafts),
                'ref_id': batch_drafts[0].id  # Use first draft ID for verification link
            })

        # Sort by created_at descending
        draft_batches.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('installations/index.html',
                         distributions=installations,
                         drafts=drafts,
                         draft_batches=draft_batches,
                         active_batches=active_batches,
                         units=units,
                         field_staffs=field_staffs,
                         task_type_filter=task_type_filter,
                         pagination=pagination)


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
            warehouse_id=get_user_warehouse_id(current_user),
            status='available'
        ).all()
        form.item_detail_id.choices = [(i.id, f"{i.item.name} - {i.serial_number}") for i in available_items]
    else:
        available_items = ItemDetail.query.filter_by(status='available').all()
        form.item_detail_id.choices = [(i.id, f"{i.item.name} - {i.serial_number}") for i in available_items]

    form.field_staff_id.choices = [(u.id, u.name) for u in User.query.filter_by(role='field_staff').all()]
    form.unit_id.choices = [(u.id, u.name) for u in Unit.query.all()]

    # Load all room details from all buildings
    from app.models.facilities import UnitDetail
    from app.models import Building

    all_rooms = UnitDetail.query.join(Building).order_by(Building.code, UnitDetail.room_name).all()

    # Format: "GD.A - GD.A 0201"
    form.unit_detail_id.choices = [(0, '-- Pilih Ruangan --')] + [
        (room.id, f"{room.building.code} - {room.room_name}")
        for room in all_rooms
    ]

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

        # Send email notification to admin
        notify_distribution_received(distribution)

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
    if current_user.is_warehouse_staff() and distribution.warehouse_id != get_user_warehouse_id(current_user):
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


@bp.route('/batch/<int:id>/detail')
@login_required
def batch_detail(id):
    """View batch distribution detail (all items in the same batch)"""
    from datetime import timedelta
    from sqlalchemy import and_

    # Get the reference distribution
    ref_distribution = Distribution.query.get_or_404(id)

    # Get all distributions from the same batch
    # For active distributions, group by: creator_id (draft_created_by or field_staff_id), unit_id, created_at (within 1 minute)
    creator_id = ref_distribution.draft_created_by if ref_distribution.draft_created_by else ref_distribution.field_staff_id
    time_window = ref_distribution.created_at.replace(second=0, microsecond=0)
    time_threshold = time_window - timedelta(seconds=59)
    time_upper = time_window + timedelta(seconds=59)

    if ref_distribution.is_draft:
        # For drafts, include draft_notes in batch key
        batch_distributions = Distribution.query.filter(
            and_(
                Distribution.is_draft == True,
                Distribution.draft_created_by == ref_distribution.draft_created_by,
                Distribution.unit_id == ref_distribution.unit_id,
                Distribution.created_at >= time_threshold,
                Distribution.created_at <= time_upper,
                Distribution.draft_notes == ref_distribution.draft_notes
            )
        ).all()
    else:
        # For active distributions
        batch_distributions = Distribution.query.filter(
            and_(
                Distribution.is_draft == False,
                Distribution.unit_id == ref_distribution.unit_id,
                Distribution.created_at >= time_threshold,
                Distribution.created_at <= time_upper,
                db.or_(
                    Distribution.draft_created_by == creator_id,
                    Distribution.field_staff_id == creator_id
                )
            )
        ).all()

    # Group items by unit_detail for better display
    items_by_location = {}
    for dist in batch_distributions:
        location_key = dist.unit_detail_id if dist.unit_detail_id else 'main'
        if location_key not in items_by_location:
            items_by_location[location_key] = {
                'unit_detail': dist.unit_detail,
                'item_list': []
            }
        if dist.item_detail:
            items_by_location[location_key]['item_list'].append(dist.item_detail)

    # Get creator info
    creator = None
    if ref_distribution.draft_created_by:
        creator = ref_distribution.draft_creator
    elif ref_distribution.field_staff_id:
        creator = User.query.get(ref_distribution.field_staff_id)

    # Determine if this batch requires admin verification
    # If created by warehouse staff (has draft_created_by), show verification step
    # If created by admin (no draft_created_by), it doesn't require verification
    requires_verification = ref_distribution.draft_created_by is not None

    # Get distributions that have verification photos (received by unit)
    # Check both individual distribution photos and distribution group photos
    verified_distributions = []
    for dist in batch_distributions:
        # Check if distribution has individual verification photo
        if dist.verification_photo is not None:
            verified_distributions.append(dist)
        # Check if distribution belongs to a group with verification photo
        elif dist.distribution_group and dist.distribution_group.verification_photo is not None:
            verified_distributions.append(dist)

    return render_template('installations/batch_detail.html',
                         ref_distribution=ref_distribution,
                         batch_distributions=batch_distributions,
                         items_by_location=items_by_location,
                         total_items=len(batch_distributions),
                         creator=creator,
                         requires_verification=requires_verification,
                         verified_distributions=verified_distributions)


@bp.route('/<int:id>/update/<string:status>', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def update_status(id, status):
    """Update distribution status"""
    distribution = Distribution.query.get_or_404(id)

    # Check access for warehouse staff
    if current_user.is_warehouse_staff() and distribution.warehouse_id != get_user_warehouse_id(current_user):
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
            print(f"Current warehouse staff warehouse_id: {get_user_warehouse_id(current_user)}")
            print(f"=================================")

            flash(f'Berhasil membuat {len(distributions_created)} distribusi untuk permohonan aset #{asset_request.id}! Field staff akan menerima task.', 'success')
            return redirect(url_for('installations.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show confirmation
    return render_template('installations/distribute_asset_request.html', asset_request=asset_request)


# ==============================================================================
# GENERAL DISTRIBUTION (Distribusi Aset Umum)
# ==============================================================================

@bp.route('/general-distribution/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def create_general_distribution():
    """Create draft distributions for general asset distribution"""
    from app.models import Warehouse, DistributionGroup

    if request.method == 'POST':
        try:
            # Get form data
            unit_id = request.form.get('unit_id', type=int)
            notes = request.form.get('notes', '')

            # Get warehouse
            warehouse_id = get_user_warehouse_id(current_user) if current_user.is_warehouse_staff() else request.form.get('warehouse_id', type=int)

            if not unit_id:
                flash('Silakan pilih unit tujuan.', 'warning')
                return redirect(url_for('installations.create_general_distribution'))

            # Get unit
            unit = Unit.query.get(unit_id)
            if not unit:
                flash('Unit tidak ditemukan.', 'danger')
                return redirect(url_for('installations.create_general_distribution'))

            # Collect item data with their unit details
            items_to_distribute = []
            for key in request.form.keys():
                if key.startswith('selected_serials_'):
                    item_num = key.replace('selected_serials_', '')
                    serials_str = request.form.get(key)

                    if serials_str:
                        unit_detail_key = f'unit_detail_{item_num}'
                        unit_detail_id = request.form.get(unit_detail_key, type=int) or None

                        serial_ids = [int(s) for s in serials_str.split(',') if s.strip()]
                        items_to_distribute.append({
                            'serial_ids': serial_ids,
                            'unit_detail_id': unit_detail_id
                        })

            if not items_to_distribute:
                flash('Silakan pilih minimal satu barang.', 'warning')
                return redirect(url_for('installations.create_general_distribution'))

            # Collect all serial IDs and validate
            all_serial_ids = []
            for item in items_to_distribute:
                all_serial_ids.extend(item['serial_ids'])

            # Validate all item details are available
            item_details = ItemDetail.query.filter(ItemDetail.id.in_(all_serial_ids)).all()
            if len(item_details) != len(all_serial_ids):
                flash('Beberapa barang tidak ditemukan.', 'danger')
                return redirect(url_for('installations.create_general_distribution'))

            for item_detail in item_details:
                if item_detail.status != 'available':
                    flash(f'Barang {item_detail.serial_number} tidak tersedia.', 'danger')
                    return redirect(url_for('installations.create_general_distribution'))

            # Create a DistributionGroup for this batch
            batch_code = DistributionGroup.generate_batch_code()
            distribution_group = DistributionGroup(
                name=f"Batch {batch_code}",
                batch_code=batch_code,
                created_by=current_user.id,
                warehouse_id=warehouse_id,
                unit_id=unit_id,
                notes=notes,
                is_draft=True,
                status='pending'
            )
            distribution_group.save()

            # Create draft distributions for each selected item
            distributions_created = []
            for item_group in items_to_distribute:
                group_item_details = ItemDetail.query.filter(ItemDetail.id.in_(item_group['serial_ids'])).all()

                for item_detail in group_item_details:
                    distribution = Distribution(
                        item_detail_id=item_detail.id,
                        warehouse_id=warehouse_id,
                        unit_id=unit_id,
                        unit_detail_id=item_group['unit_detail_id'],
                        address=unit.address if unit else 'Unknown',
                        status='draft',
                        is_draft=True,
                        draft_created_by=current_user.id,
                        draft_notes=notes,
                        distribution_group_id=distribution_group.id  # Link to distribution group
                    )

                    # Set coordinates from unit if available
                    if unit and unit.geom:
                        distribution.geom = unit.geom

                    distribution.save()
                    distributions_created.append(distribution)

            # If admin, directly approve (verify) all drafts in this batch
            if current_user.is_admin():
                success, message = distribution_group.approve(current_user.id)
                if success:
                    # Send email notification to unit staff
                    for dist in distribution_group.distributions:
                        notify_distribution_sent(dist)

                    flash(f'{len(distributions_created)} distribusi berhasil dibuat dan disetujui.', 'success')
                else:
                    flash(message, 'danger')
            else:
                # Send email notification to admin about new draft distribution
                notify_distribution_created(distributions_created[0] if distributions_created else None)

                flash(f'{len(distributions_created)} draft distribusi berhasil dibuat. Menunggu verifikasi admin.', 'success')

            return redirect(url_for('installations.index'))

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show form
    from app.models.facilities import UnitDetail
    from app.models import Building

    warehouses = Warehouse.query.all() if current_user.is_admin() else []
    units = Unit.query.all()
    items = Item.query.all()

    # Get all rooms from all buildings for unit_detail dropdown
    all_rooms = UnitDetail.query.join(Building).order_by(Building.code, UnitDetail.room_name).all()

    # Format: "GD.A - GD.A 0201"
    unit_details_choices = [(room.id, f"{room.building.code} - {room.room_name}") for room in all_rooms]

    # Get warehouse_id for current user
    user_warehouse_id = get_user_warehouse_id(current_user)

    return render_template('installations/create_general_distribution.html',
                         warehouses=warehouses,
                         units=units,
                         items=items,
                         unit_details=unit_details_choices,
                         user_warehouse_id=user_warehouse_id)


@bp.route('/general-distribution/<int:id>/verify')
@login_required
@role_required('admin')
def verify_general_distribution(id):
    """Verify and approve/reject draft distribution batch using DistributionGroup"""
    from app.models import DistributionGroup

    # Get the reference distribution
    ref_distribution = Distribution.query.get_or_404(id)

    if not ref_distribution.is_draft:
        flash('Ini bukan draft distribusi.', 'warning')
        return redirect(url_for('installations.index'))

    # Get the distribution group
    if not ref_distribution.distribution_group_id:
        flash('Draft distribusi ini tidak terkait dengan batch manapun.', 'warning')
        return redirect(url_for('installations.index'))

    distribution_group = DistributionGroup.query.get_or_404(ref_distribution.distribution_group_id)

    # Get all distributions in this group
    batch_distributions = distribution_group.distributions

    # Group items by unit_detail for better display
    items_by_location = {}
    for dist in batch_distributions:
        location_key = dist.unit_detail_id if dist.unit_detail_id else 'main'
        if location_key not in items_by_location:
            items_by_location[location_key] = {
                'unit_detail': dist.unit_detail,
                'item_list': []
            }
        if dist.item_detail:
            items_by_location[location_key]['item_list'].append(dist.item_detail)

    return render_template('installations/verify_general_distribution.html',
                         ref_distribution=ref_distribution,
                         distribution_group=distribution_group,
                         batch_distributions=batch_distributions,
                         items_by_location=items_by_location,
                         total_items=len(batch_distributions))


@bp.route('/general-distribution/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_general_distribution(id):
    """Approve all draft distributions in the same batch using DistributionGroup"""
    from app.models import DistributionGroup

    # Get the reference distribution
    ref_distribution = Distribution.query.get_or_404(id)

    if not ref_distribution.is_draft:
        return jsonify({'success': False, 'message': 'Ini bukan draft distribusi'}), 400

    if not ref_distribution.distribution_group_id:
        return jsonify({'success': False, 'message': 'Draft distribusi ini tidak terkait dengan batch manapun'}), 400

    try:
        # Get the distribution group
        distribution_group = DistributionGroup.query.get_or_404(ref_distribution.distribution_group_id)

        # Approve the entire group
        success, message = distribution_group.approve(current_user.id)

        if success:
            # Send email notification to unit staff for each distribution
            for dist in distribution_group.distributions:
                notify_distribution_sent(dist)

            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('installations.index'))


@bp.route('/general-distribution/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_general_distribution(id):
    """Reject all draft distributions in the same batch using DistributionGroup"""
    from app.models import DistributionGroup

    # Get the reference distribution
    ref_distribution = Distribution.query.get_or_404(id)

    if not ref_distribution.is_draft:
        return jsonify({'success': False, 'message': 'Ini bukan draft distribusi'}), 400

    if not ref_distribution.distribution_group_id:
        return jsonify({'success': False, 'message': 'Draft distribusi ini tidak terkait dengan batch manapun'}), 400

    reason = request.form.get('reason', '')

    try:
        # Get the distribution group
        distribution_group = DistributionGroup.query.get_or_404(ref_distribution.distribution_group_id)

        # Reject the entire group
        success, message = distribution_group.reject(current_user.id, reason)

        if success:
            # Send email notification to warehouse staff who created the draft
            for dist in distribution_group.distributions:
                if dist.draft_created_by:
                    notify_distribution_rejected(dist, reason)

            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('installations.index'))


@bp.route('/api/available-items/<int:warehouse_id>/<int:item_id>')
@login_required
@role_required('warehouse_staff', 'admin')
def api_available_items_general(warehouse_id, item_id):
    """API endpoint to get available item details for general distribution"""
    from sqlalchemy import and_, not_

    # Subquery to find item_detail_ids that have active distributions
    # (Rejected distributions are moved to rejected_distributions table, so not here)
    active_distribution_ids = db.session.query(
        Distribution.item_detail_id
    ).filter(
        Distribution.item_detail_id.isnot(None)
    ).subquery()

    # Get available items that:
    # 1. Are in the specified warehouse
    # 2. Match the item type
    # 3. Have status 'available'
    # 4. Don't have any active distributions
    available_items = ItemDetail.query.filter(
        and_(
            ItemDetail.warehouse_id == warehouse_id,
            ItemDetail.item_id == item_id,
            ItemDetail.status == 'available',
            not_(ItemDetail.id.in_(active_distribution_ids))
        )
    ).all()

    items_data = [{
        'id': item.id,
        'serial_number': item.serial_number,
        'serial_unit': item.serial_unit or '-'
    } for item in available_items]

    return jsonify({
        'success': True,
        'items': items_data,
        'total': len(items_data)
    })


@bp.route('/api/unit/<int:unit_id>/details')
@login_required
def api_unit_details(unit_id):
    """API endpoint to get all rooms from all buildings"""
    try:
        # Get all rooms from all buildings, ordered by building code then room name
        from app.models import Building
        unit_details = UnitDetail.query.join(Building).order_by(Building.code, UnitDetail.room_name).all()

        details_data = [{
            'id': ud.id,
            'room_name': f"{ud.building.code} - {ud.room_name}",  # Format: GD.A - GD.A 0201
            'floor': ud.floor,
            'building_code': ud.building.code
        } for ud in unit_details]

        return jsonify({
            'success': True,
            'details': details_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
