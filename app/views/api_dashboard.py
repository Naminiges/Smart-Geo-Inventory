from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.helpers import get_dashboard_stats, get_user_warehouse_id

bp = Blueprint('api_dashboard', __name__)


@bp.route('/stats')
@login_required
def api_stats():
    """Get dashboard statistics"""
    warehouse_id = get_user_warehouse_id(current_user) if current_user.is_warehouse_staff() else None
    stats = get_dashboard_stats(warehouse_id)

    return jsonify({
        'success': True,
        'stats': stats
    })


@bp.route('/warehouse-stats')
@login_required
@role_required('warehouse_staff')
def api_warehouse_stats():
    """Get warehouse-specific statistics"""
    warehouse_id = get_user_warehouse_id(current_user)
    stats = get_dashboard_stats(warehouse_id)

    return jsonify({
        'success': True,
        'stats': stats,
        'warehouse': {
            'id': current_user.warehouse.id,
            'name': current_user.warehouse.name,
            'address': current_user.warehouse.address
        } if current_user.warehouse else None
    })


@bp.route('/admin-stats')
@login_required
@role_required('admin')
def api_admin_stats():
    """Get admin dashboard statistics"""
    stats = get_dashboard_stats()

    return jsonify({
        'success': True,
        'stats': stats
    })
