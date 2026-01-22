from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.helpers import get_dashboard_stats, get_user_warehouse_id

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('/')
@login_required
def index():
    """Main dashboard - redirect based on role"""
    if current_user.is_admin():
        return redirect(url_for('dashboard.admin_index'))
    elif current_user.is_warehouse_staff():
        return redirect(url_for('dashboard.warehouse_index'))
    elif current_user.is_field_staff():
        return redirect(url_for('dashboard.field_index'))
    elif current_user.is_unit_staff():
        return redirect(url_for('dashboard.unit_index'))
    else:
        return redirect(url_for('auth.logout'))


@bp.route('/warehouse')
@login_required
@role_required('warehouse_staff')
def warehouse_index():
    """Warehouse staff dashboard"""
    from app.models import AssetRequest
    from app.models.user import UserWarehouse

    # Get warehouse from UserWarehouse relationship
    warehouse_id = get_user_warehouse_id(current_user)

    if warehouse_id:
        from app.models import Warehouse
        warehouse = Warehouse.query.get(warehouse_id)
    else:
        warehouse = None

    stats = get_dashboard_stats(warehouse_id)

    # Get verified asset requests count for warehouse staff (filtered by warehouse)
    verified_request_count = AssetRequest.query.filter_by(status='verified').count()

    return render_template('dashboard/warehouse_index.html',
                         stats=stats,
                         warehouse=warehouse,
                         user=current_user,
                         verified_request_count=verified_request_count)


@bp.route('/admin')
@login_required
@role_required('admin')
def admin_index():
    """Admin dashboard"""
    from app.models import AssetRequest, UserUnit, Unit

    stats = get_dashboard_stats()

    # Get pending request count (units with pending status)
    pending_request_count = Unit.query.filter_by(status='pending').count()

    # Get verified asset requests count
    verified_request_count = AssetRequest.query.filter_by(status='verified').count()

    return render_template('dashboard/admin_index.html',
                         stats=stats,
                         user=current_user,
                         pending_request_count=pending_request_count,
                         verified_request_count=verified_request_count)


@bp.route('/field')
@login_required
@role_required('field_staff')
def field_index():
    """Field staff dashboard"""
    from app.models import Distribution

    # Get distributions for current field staff - convert to list
    distributions = Distribution.query.filter_by(field_staff_id=current_user.id).all()
    distributions_list = list(distributions)

    # Calculate stats
    total_distributions = len(distributions_list)
    pending_count = len([d for d in distributions_list if d.status == 'pending'])
    completed_count = len([d for d in distributions_list if d.status == 'completed'])
    in_transit_count = len([d for d in distributions_list if d.status == 'in_transit'])

    return render_template('dashboard/field_index.html',
                         distributions=distributions_list,
                         total_distributions=total_distributions,
                         pending_count=pending_count,
                         completed_count=completed_count,
                         in_transit_count=in_transit_count,
                         user=current_user)


@bp.route('/unit')
@login_required
@role_required('unit_staff')
def unit_index():
    """Unit staff dashboard"""
    from app.models import Unit

    # Get only units assigned to current unit staff
    units = current_user.get_assigned_units()
    units_list = list(units)  # Convert query to list

    # Calculate stats - handle unit_details as query object
    total_units = len(units_list)
    units_with_items = 0
    available_units = 0
    maintenance_units = 0

    for unit in units_list:
        # Check if unit has items - convert to list first
        if unit.unit_details:
            unit_details_list = list(unit.unit_details)
            if len(unit_details_list) > 0:
                units_with_items += 1

        # Count by status
        if unit.status == 'available':
            available_units += 1
        elif unit.status == 'maintenance':
            maintenance_units += 1

    return render_template('dashboard/unit_index.html',
                         units=units_list,
                         total_units=total_units,
                         units_with_items=units_with_items,
                         available_units=available_units,
                         maintenance_units=maintenance_units,
                         user=current_user)

