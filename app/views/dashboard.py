from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.helpers import get_dashboard_stats

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
    else:
        return redirect(url_for('auth.logout'))


@bp.route('/warehouse')
@login_required
@role_required('warehouse_staff')
def warehouse_index():
    """Warehouse staff dashboard"""
    warehouse_id = current_user.warehouse_id
    stats = get_dashboard_stats(warehouse_id)

    return render_template('dashboard/warehouse_index.html',
                         stats=stats,
                         warehouse=current_user.warehouse,
                         user=current_user)


@bp.route('/admin')
@login_required
@role_required('admin')
def admin_index():
    """Admin dashboard"""
    stats = get_dashboard_stats()

    return render_template('dashboard/admin_index.html',
                         stats=stats,
                         user=current_user)


@bp.route('/field')
@login_required
@role_required('field_staff')
def field_index():
    """Field staff dashboard"""
    from app.models import Distribution

    # Get distributions for current field staff
    distributions = Distribution.query.filter_by(field_staff_id=current_user.id).all()

    return render_template('dashboard/field_index.html',
                         distributions=distributions,
                         user=current_user)
