from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.master_data import Warehouse, Item, ItemDetail
from app.models.inventory import Stock
from app.forms.warehouse_forms import WarehouseForm
from app import db
from app.utils.decorators import role_required

bp = Blueprint('warehouses', __name__, url_prefix='/warehouses')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """List all warehouses"""
    warehouses = Warehouse.query.all()

    # Calculate total stock for each warehouse
    warehouse_data = []
    for warehouse in warehouses:
        total_stock = db.session.query(db.func.sum(Stock.quantity)).filter(
            Stock.warehouse_id == warehouse.id
        ).scalar() or 0

        warehouse_data.append({
            'warehouse': warehouse,
            'total_stock': total_stock
        })

    return render_template('warehouses/index.html', warehouse_data=warehouse_data)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create a new warehouse"""
    form = WarehouseForm()

    if form.validate_on_submit():
        try:
            warehouse = Warehouse(
                name=form.name.data,
                address=form.address.data
            )

            # Set coordinates if provided
            if form.latitude.data is not None and form.longitude.data is not None:
                warehouse.set_coordinates(form.latitude.data, form.longitude.data)

            warehouse.save()
            flash(f'Gudang {warehouse.name} berhasil ditambahkan!', 'success')
            return redirect(url_for('warehouses.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('warehouses/create.html', form=form)


@bp.route('/<int:id>', methods=['GET'])
@login_required
@role_required('admin')
def detail(id):
    """View warehouse details with items"""
    warehouse = Warehouse.query.get_or_404(id)

    # Get stocks in this warehouse
    stocks = Stock.query.filter_by(warehouse_id=id).all()

    # Get item details in this warehouse, ordered by status
    # Order: available, used, in_unit, maintenance, processing, returned
    status_order = db.case(
        (ItemDetail.status == 'available', 1),
        (ItemDetail.status == 'used', 2),
        (ItemDetail.status == 'in_unit', 3),
        (ItemDetail.status == 'maintenance', 4),
        (ItemDetail.status == 'processing', 5),
        (ItemDetail.status == 'returned', 6),
        else_=7
    )
    item_details = ItemDetail.query.filter_by(warehouse_id=id).order_by(status_order).all()

    # Calculate statistics
    total_items = len(stocks)
    total_quantity = sum(stock.quantity for stock in stocks)
    total_item_details = len(item_details)

    # Count by status
    available_details = ItemDetail.query.filter_by(warehouse_id=id, status='available').count()
    used_details = ItemDetail.query.filter_by(warehouse_id=id, status='used').count()
    in_unit_details = ItemDetail.query.filter_by(warehouse_id=id, status='in_unit').count()
    maintenance_details = ItemDetail.query.filter_by(warehouse_id=id, status='maintenance').count()

    return render_template('warehouses/detail.html',
                         warehouse=warehouse,
                         stocks=stocks,
                         item_details=item_details,
                         total_items=total_items,
                         total_quantity=total_quantity,
                         total_item_details=total_item_details,
                         available_details=available_details,
                         used_details=used_details,
                         in_unit_details=in_unit_details,
                         maintenance_details=maintenance_details)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit warehouse"""
    warehouse = Warehouse.query.get_or_404(id)
    form = WarehouseForm()

    if form.validate_on_submit():
        try:
            warehouse.name = form.name.data
            warehouse.address = form.address.data

            # Update coordinates if provided
            if form.latitude.data is not None and form.longitude.data is not None:
                warehouse.set_coordinates(form.latitude.data, form.longitude.data)

            warehouse.save()
            flash(f'Gudang {warehouse.name} berhasil diperbarui!', 'success')
            return redirect(url_for('warehouses.detail', id=id))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    else:
        # Pre-fill form with existing data
        form.name.data = warehouse.name
        form.address.data = warehouse.address

        # Get existing coordinates
        coords = warehouse.get_coordinates()
        if coords:
            form.latitude.data = coords['latitude']
            form.longitude.data = coords['longitude']

    return render_template('warehouses/edit.html', form=form, warehouse=warehouse)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete warehouse"""
    warehouse = Warehouse.query.get_or_404(id)

    # Check if warehouse has stocks or item details
    stock_count = Stock.query.filter_by(warehouse_id=id).count()
    item_detail_count = ItemDetail.query.filter_by(warehouse_id=id).count()
    user_count = warehouse.users.count()

    if stock_count > 0 or item_detail_count > 0 or user_count > 0:
        flash(f'Gudang {warehouse.name} tidak dapat dihapus karena masih memiliki data terkait!', 'danger')
        return redirect(url_for('warehouses.index'))

    try:
        warehouse.delete()
        flash(f'Gudang {warehouse.name} berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('warehouses.index'))
