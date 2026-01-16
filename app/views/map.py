from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.models import Warehouse, Unit, Distribution, ItemDetail

bp = Blueprint('map', __name__, url_prefix='/map')


@bp.route('/')
@login_required
def index():
    """Main map page"""
    return render_template('map/index.html', user=current_user)


@bp.route('/warehouses')
@login_required
def warehouses():
    """Map showing all warehouses"""
    warehouses = Warehouse.query.all()

    return render_template('map/warehouses.html',
                         warehouses=warehouses,
                         user=current_user)


@bp.route('/units')
@login_required
def units():
    """Map showing all units/buildings"""
    units = Unit.query.all()

    return render_template('map/units.html',
                         units=units,
                         user=current_user)


@bp.route('/distributions')
@login_required
def distributions():
    """Map showing all distributions"""
    distributions = Distribution.query.all()

    return render_template('map/distributions.html',
                         distributions=distributions,
                         user=current_user)


@bp.route('/assets')
@login_required
def assets():
    """Map showing all assets"""
    # Get available items in warehouses
    items = ItemDetail.query.filter_by(status='available').all()

    return render_template('map/assets.html',
                         items=items,
                         user=current_user)
