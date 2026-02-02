from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import ReturnBatch, ReturnItem, Distribution, ItemDetail, UserWarehouse, Warehouse, Unit
from app.utils.decorators import role_required
from datetime import datetime
import json

bp = Blueprint('returns', __name__, url_prefix='/returns')


def get_user_warehouse_id():
    """Get warehouse ID for current user"""
    if current_user.is_admin():
        return None
    user_warehouse = UserWarehouse.query.filter_by(user_id=current_user.id).first()
    return user_warehouse.warehouse_id if user_warehouse else None


@bp.route('/', methods=['GET'])
@login_required
@role_required('warehouse_staff', 'admin')
def index():
    """List all return batches for warehouse staff"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 10 items per page

    warehouse_id = get_user_warehouse_id()

    # Build query
    query = ReturnBatch.query

    # Filter by warehouse for non-admin users
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)

    # Server-side pagination
    pagination = query.order_by(ReturnBatch.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return_batches = pagination.items

    return render_template('returns/index.html',
                          return_batches=return_batches,
                          pagination=pagination)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def create():
    """Create a new return batch"""
    print(f'\n\n=== CREATE ROUTE CALLED ===')
    print(f'Request method: {request.method}')
    print(f'Request form keys: {list(request.form.keys())}')
    print(f'Request args: {dict(request.args)}')

    warehouse_id = get_user_warehouse_id()

    if not warehouse_id and not current_user.is_admin():
        flash('Anda belum terassign ke warehouse manapun.', 'danger')
        return redirect(url_for('returns.index'))

    if request.method == 'POST':
        try:
            # Get form data
            return_date_str = request.form.get('return_date')
            notes = request.form.get('notes', '')
            selected_warehouse_id = request.form.get('warehouse_id', type=int)

            # Admin can select warehouse, staff uses assigned warehouse
            if current_user.is_admin() and selected_warehouse_id:
                final_warehouse_id = selected_warehouse_id
            else:
                final_warehouse_id = warehouse_id

            if not final_warehouse_id:
                flash('Warehouse harus dipilih.', 'danger')
                return redirect(url_for('returns.create'))

            # Parse return date
            try:
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Format tanggal tidak valid.', 'danger')
                return redirect(url_for('returns.create'))

            # Generate batch code
            batch_code = ReturnBatch.generate_batch_code(final_warehouse_id)

            # Create return batch
            return_batch = ReturnBatch(
                batch_code=batch_code,
                warehouse_id=final_warehouse_id,
                return_date=return_date,
                notes=notes,
                created_by=current_user.id
            )
            return_batch.save()

            # Get selected items from form - try multiple methods
            # First try as single string value (from FormData.append)
            items_json = request.form.get('items')
            print(f'DEBUG - items from request.form.get: {items_json}')

            # If not found, try as list
            if not items_json:
                item_data = request.form.getlist('items[]')
                if item_data:
                    items_json = item_data[0]

            print(f'DEBUG - Final items_json: {items_json}')
            print(f'DEBUG - request.form keys: {list(request.form.keys())}')
            print(f'DEBUG - request.form values: {list(request.form.values())}')

            if not items_json:
                return_batch.delete()
                flash('Pilih minimal satu item untuk diretur.', 'warning')
                return redirect(url_for('returns.create'))

            # Add items to return batch
            success_count = 0

            try:
                print(f'DEBUG - Parsing items_json: {items_json}')
                items_list = json.loads(items_json)
                print(f'DEBUG - Parsed items_list: {items_list}')
                print(f'DEBUG - items_list type: {type(items_list)}')

                # Check if it's a list of items
                if isinstance(items_list, list):
                    # Process each item in the list
                    for item_info in items_list:
                        print(f'DEBUG - Processing individual item: {item_info}')
                        return_item = ReturnItem(
                            return_batch_id=return_batch.id,
                            item_detail_id=item_info['item_detail_id'],
                            unit_id=item_info['unit_id'],
                            distribution_id=item_info.get('distribution_id'),
                            return_reason=item_info.get('return_reason', ''),
                            condition=item_info.get('condition', 'good'),
                            condition_notes=item_info.get('condition_notes', '')
                        )
                        return_item.save()
                        success_count += 1
                        print(f'DEBUG - Successfully saved item {success_count}')
                else:
                    print(f'DEBUG - items_list is not a list, cannot process')

            except Exception as e:
                print(f'DEBUG - Error parsing items: {str(e)}')
                print(f'DEBUG - Items JSON was: {items_json}')
                import traceback
                traceback.print_exc()

            print(f'DEBUG - Total items saved: {success_count}')

            if success_count == 0:
                return_batch.delete()
                flash('Tidak ada item yang berhasil disimpan. Silakan coba lagi.', 'danger')
                return redirect(url_for('returns.create'))

            flash(f'Batch retur {batch_code} berhasil dibuat dengan {success_count} item.', 'success')
            return redirect(url_for('returns.detail', id=return_batch.id))

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show create form
    # Get available warehouses (admin only)
    warehouses = []
    if current_user.is_admin():
        warehouses = Warehouse.query.all()

    # Get distributions that can be returned (items with status 'installed' or 'used')
    # Only show items from user's warehouse
    # Also exclude items that are already in a return batch
    # Get item_detail_ids that are already in return batches
    existing_return_item_ids = db.session.query(ReturnItem.item_detail_id).filter(
        ReturnItem.status.in_(['pending', 'returned'])
    ).all()
    existing_return_item_ids = [id[0] for id in existing_return_item_ids]

    dist_query = Distribution.query.filter(
        Distribution.status.in_(['installed', 'broken', 'maintenance']),
        Distribution.verification_status == 'submitted'
    ).join(ItemDetail).filter(
        ItemDetail.status.in_(['used', 'in_unit']),
        ~ItemDetail.id.in_(existing_return_item_ids)  # Exclude items already in return batches
    )

    if warehouse_id:
        dist_query = dist_query.filter(Distribution.warehouse_id == warehouse_id)

    distributions = dist_query.order_by(Distribution.verified_at.desc()).all()

    return render_template('returns/create.html',
                         warehouses=warehouses,
                         warehouse_id=warehouse_id,
                         distributions=distributions)


@bp.route('/<int:id>', methods=['GET'])
@login_required
@role_required('warehouse_staff', 'admin')
def detail(id):
    """Show return batch details"""
    warehouse_id = get_user_warehouse_id()

    return_batch = ReturnBatch.query.get_or_404(id)

    # Check permission
    if warehouse_id and return_batch.warehouse_id != warehouse_id:
        flash('Anda tidak memiliki izin untuk mengakses batch retur ini.', 'danger')
        return redirect(url_for('returns.index'))

    return render_template('returns/detail.html', return_batch=return_batch)


@bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def confirm(id):
    """Confirm a return batch"""
    warehouse_id = get_user_warehouse_id()

    return_batch = ReturnBatch.query.get_or_404(id)

    # Check permission
    if warehouse_id and return_batch.warehouse_id != warehouse_id:
        flash('Anda tidak memiliki izin untuk mengkonfirmasi batch retur ini.', 'danger')
        return redirect(url_for('returns.index'))

    # Confirm the return
    success, message = return_batch.confirm(current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('returns.detail', id=id))


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def cancel(id):
    """Cancel a return batch"""
    warehouse_id = get_user_warehouse_id()

    return_batch = ReturnBatch.query.get_or_404(id)

    # Check permission
    if warehouse_id and return_batch.warehouse_id != warehouse_id:
        flash('Anda tidak memiliki izin untuk membatalkan batch retur ini.', 'danger')
        return redirect(url_for('returns.index'))

    # Get cancellation reason
    reason = request.form.get('reason', '')

    # Cancel the return
    success, message = return_batch.cancel(current_user.id, reason)

    if success:
        flash(message, 'warning')
    else:
        flash(message, 'danger')

    return redirect(url_for('returns.detail', id=id))


@bp.route('/api/distributions', methods=['GET'])
@login_required
@role_required('warehouse_staff', 'admin')
def api_distributions():
    """API to get distributions for return (AJAX)"""
    warehouse_id = get_user_warehouse_id()

    # Get query parameters
    unit_id = request.args.get('unit_id', type=int)
    search = request.args.get('search', '')

    # Build query
    query = Distribution.query.filter(
        Distribution.verification_status == 'submitted',
        Distribution.status.in_(['installed', 'broken', 'maintenance'])
    ).join(ItemDetail).filter(
        ItemDetail.status.in_(['used', 'in_unit'])
    )

    # Filter by warehouse
    if warehouse_id:
        query = query.filter(Distribution.warehouse_id == warehouse_id)

    # Filter by unit
    if unit_id:
        query = query.filter(Distribution.unit_id == unit_id)

    # Search by item name or serial number
    if search:
        from app.models import Item
        query = query.join(Item).filter(
            db.or_(
                Item.name.ilike(f'%{search}%'),
                ItemDetail.serial_number.ilike(f'%{search}%')
            )
        )

    distributions = query.order_by(Distribution.verified_at.desc()).limit(50).all()

    # Format response
    result = []
    for dist in distributions:
        result.append({
            'id': dist.id,
            'item_name': dist.item_detail.item.name if dist.item_detail and dist.item_detail.item else 'Unknown',
            'serial_number': dist.item_detail.serial_number if dist.item_detail else '',
            'unit_name': dist.unit.name if dist.unit else 'Unknown',
            'unit_id': dist.unit_id,
            'item_detail_id': dist.item_detail_id,
            'verified_at': dist.verified_at.strftime('%Y-%m-%d %H:%M') if dist.verified_at else ''
        })

    return jsonify(result)
