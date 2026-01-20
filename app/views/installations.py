from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Distribution, ItemDetail, User, Unit, UnitDetail, AssetRequest, AssetRequestItem
from app.forms import DistributionForm, InstallationForm
from app.utils.decorators import role_required, warehouse_access_required

bp = Blueprint('installations', __name__, url_prefix='/installations')


@bp.route('/')
@login_required
@warehouse_access_required
def index():
    """List all installations and verified asset requests"""
    if current_user.is_warehouse_staff():
        installations = Distribution.query.filter_by(warehouse_id=current_user.warehouse_id).all()
        # Get verified asset requests that haven't been distributed yet
        verified_requests = AssetRequest.query.filter_by(status='verified').all()
        # Filter to only show requests that don't have a distribution yet
        verified_requests = [req for req in verified_requests if req.distribution_id is None]
    elif current_user.is_field_staff():
        installations = Distribution.query.filter_by(field_staff_id=current_user.id).all()
        verified_requests = []
    else:  # admin
        installations = Distribution.query.all()
        verified_requests = AssetRequest.query.filter_by(status='verified', distribution_id=None).all()

    return render_template('installations/index.html',
                         installations=installations,
                         verified_requests=verified_requests)


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
    """Verify installation completion"""
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


@bp.route('/<int:id>/detail')
@login_required
def detail(id):
    """View installation detail"""
    installation = Distribution.query.get_or_404(id)
    return render_template('installations/detail.html', installation=installation)


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
    asset_request = AssetRequest.query.get_or_404(request_id)

    if asset_request.status != 'verified':
        flash('Hanya permohonan yang sudah diverifikasi yang dapat diproses.', 'warning')
        return redirect(url_for('installations.index'))

    if asset_request.distribution_id:
        flash('Permohonan ini sudah memiliki distribusi.', 'info')
        return redirect(url_for('installations.index'))

    if request.method == 'POST':
        try:
            # For each item in the asset request, create a distribution
            request_items = AssetRequestItem.query.filter_by(asset_request_id=request_id).all()

            if not request_items:
                flash('Tidak ada item dalam permohonan ini.', 'danger')
                return redirect(url_for('installations.index'))

            # Create distributions for each item
            # For simplicity, we'll create one distribution per item
            distributions_created = 0

            for req_item in request_items:
                # Find available item details in warehouse
                # This is a simplified version - you may need more complex logic
                # to allocate specific items from stock

                # Get item details with available status
                available_items = ItemDetail.query.filter_by(
                    item_id=req_item.item_id,
                    status='available'
                ).limit(req_item.quantity).all()

                if len(available_items) < req_item.quantity:
                    flash(f'Stok tidak mencukupi untuk {req_item.item.name}. Tersedia: {len(available_items)}, Diminta: {req_item.quantity}', 'danger')
                    return redirect(url_for('installations.index'))

                # Create distribution record for each item
                for item_detail in available_items:
                    distribution = Distribution(
                        item_detail_id=item_detail.id,
                        warehouse_id=item_detail.warehouse_id,
                        unit_id=asset_request.unit_id,
                        unit_detail_id=req_item.unit_detail_id,
                        address=asset_request.unit.location if asset_request.unit else None,
                        note=f"Aset Request #{asset_request.id}: {req_item.room_notes or asset_request.request_notes}",
                        status='installing'
                    )

                    # Set coordinates if unit has location
                    if asset_request.unit and hasattr(asset_request.unit, 'latitude') and hasattr(asset_request.unit, 'longitude'):
                        if asset_request.unit.latitude and asset_request.unit.longitude:
                            distribution.set_coordinates(asset_request.unit.latitude, asset_request.unit.longitude)

                    distribution.save()

                    # Update item detail status
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
                        destination_id=asset_request.unit_id,
                        status_before='available',
                        status_after='processing',
                        note=f"Asset Request #{asset_request.id}: {req_item.room_notes or ''}"
                    )

                    distributions_created += 1

            # Link the asset request to the first distribution (for tracking)
            if distributions_created > 0:
                first_distribution = Distribution.query.filter_by(
                    unit_id=asset_request.unit_id,
                    note=f"Aset Request #{asset_request.id}"
                ).first()

                if first_distribution:
                    asset_request.distribution_id = first_distribution.id
                    asset_request.save()

            flash(f'Berhasil membuat {distributions_created} distribusi untuk permohonan aset #{asset_request.id}!', 'success')
            return redirect(url_for('installations.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show confirmation
    return render_template('installations/distribute_asset_request.html', asset_request=asset_request)
