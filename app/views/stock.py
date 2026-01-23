from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockTransaction, Item, Warehouse, Distribution, ReturnItem
from app.forms import StockForm, StockTransactionForm
from app.utils.decorators import role_required, warehouse_access_required
from sqlalchemy import func, and_
from datetime import datetime

bp = Blueprint('stock', __name__, url_prefix='/stock')


@bp.route('/')
@login_required
def index():
    """Stock history page with navigation buttons"""
    # Get recent stock transactions
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            transactions = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids)
            ).order_by(StockTransaction.transaction_date.desc()).limit(50).all()
        else:
            transactions = []
    else:
        transactions = StockTransaction.query.order_by(StockTransaction.transaction_date.desc()).limit(50).all()

    # Get recent distributions (items going to units)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            distributions = Distribution.query.filter(
                Distribution.warehouse_id.in_(user_warehouse_ids)
            ).order_by(Distribution.created_at.desc()).limit(50).all()
        else:
            distributions = []
    else:
        distributions = Distribution.query.order_by(Distribution.created_at.desc()).limit(50).all()

    # Get recent returns (items coming back from units)
    returns = ReturnItem.query.filter_by(status='returned').order_by(ReturnItem.created_at.desc()).limit(50).all()

    return render_template('stock/index.html',
                         transactions=transactions,
                         distributions=distributions,
                         returns=returns)


@bp.route('/recap')
@login_required
def recap():
    """Annual recap/report page"""
    year = request.args.get('year', datetime.now().year, type=int)

    # Get stock transactions per month
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            stock_in = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'IN',
                func.extract('year', StockTransaction.transaction_date) == year
            ).all()
            stock_out = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'OUT',
                func.extract('year', StockTransaction.transaction_date) == year
            ).all()
        else:
            stock_in = []
            stock_out = []
    else:
        stock_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            func.extract('year', StockTransaction.transaction_date) == year
        ).all()
        stock_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            func.extract('year', StockTransaction.transaction_date) == year
        ).all()

    # Get distributions to units
    distributions = Distribution.query.filter(
        func.extract('year', Distribution.created_at) == year
    ).all()

    # Get returns from units
    returns = ReturnItem.query.filter(
        func.extract('year', ReturnItem.created_at) == year,
        ReturnItem.status == 'returned'
    ).all()

    # Calculate totals
    total_in = sum(t.quantity for t in stock_in)
    # Total out = stock transactions OUT + distributions to units
    total_out = sum(t.quantity for t in stock_out) + len(distributions)
    total_distributed = len(distributions)
    total_returned = len(returns)

    # Group by source/destination
    in_by_source = {}
    for t in stock_in:
        source = t.warehouse.name if t.warehouse else 'Unknown'
        in_by_source[source] = in_by_source.get(source, 0) + t.quantity

    # Group stock out by warehouse
    out_by_source = {}
    for t in stock_out:
        source = t.warehouse.name if t.warehouse else 'Unknown'
        out_by_source[source] = out_by_source.get(source, 0) + t.quantity

    # Add distributions to out_by_source (group by warehouse name)
    for d in distributions:
        source = d.warehouse.name if d.warehouse else 'Unknown'
        out_by_source[source] = out_by_source.get(source, 0) + 1

    # Obname: items still in warehouse (status: available) created in selected year
    from app.models.master_data import ItemDetail
    obname_items = ItemDetail.query.filter(
        ItemDetail.status == 'available',
        func.extract('year', ItemDetail.created_at) == year
    ).all()
    total_obname = len(obname_items)

    return render_template('stock/recap.html',
                         year=year,
                         total_in=total_in,
                         total_out=total_out,
                         total_distributed=total_distributed,
                         total_returned=total_returned,
                         total_obname=total_obname,
                         in_by_source=in_by_source,
                         out_by_source=out_by_source,
                         stock_in=stock_in,
                         stock_out=stock_out,
                         distributions=distributions,
                         returns=returns,
                         obname_items=obname_items)


@bp.route('/per-unit')
@login_required
def per_unit():
    """Stock per unit with room cards"""
    from app.models import Unit, UnitDetail, ItemDetail

    # Get all units
    units = Unit.query.filter_by(status='active').all()

    unit_data = []
    for unit in units:
        # Get all rooms in this unit
        rooms = UnitDetail.query.filter_by(unit_id=unit.id).all()

        room_data = []
        for room in rooms:
            # Get item details in this room
            item_details = ItemDetail.query.join(Distribution).filter(
                Distribution.unit_detail_id == room.id
            ).all()

            # Group by item
            items_in_room = {}
            for detail in item_details:
                item_name = detail.item.name
                if item_name not in items_in_room:
                    items_in_room[item_name] = {
                        'item': detail.item,
                        'count': 0,
                        'statuses': {}
                    }
                items_in_room[item_name]['count'] += 1
                status = detail.status
                items_in_room[item_name]['statuses'][status] = items_in_room[item_name]['statuses'].get(status, 0) + 1

            room_data.append({
                'room': room,
                'items': items_in_room,
                'total_items': len(item_details)
            })

        unit_data.append({
            'unit': unit,
            'rooms': room_data,
            'total_items': sum(rd['total_items'] for rd in room_data)
        })

    return render_template('stock/per_unit.html', unit_data=unit_data)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def add():
    """Add stock transaction (IN)"""
    form = StockTransactionForm()

    # Populate choices
    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    if current_user.is_warehouse_staff():
        # Get warehouses from UserWarehouse assignments (many-to-many)
        user_warehouses = current_user.user_warehouses.all()
        if user_warehouses:
            form.warehouse_id.choices = [(uw.warehouse.id, uw.warehouse.name) for uw in user_warehouses]
        else:
            form.warehouse_id.choices = []
    else:
        form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    if form.validate_on_submit():
        try:
            # Get or create stock record
            stock = Stock.query.filter_by(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data
            ).first()

            if not stock:
                stock = Stock(
                    item_id=form.item_id.data,
                    warehouse_id=form.warehouse_id.data,
                    quantity=0
                )

            # Add stock
            if form.transaction_type.data == 'IN':
                stock.add_stock(form.quantity.data)
            else:
                if not stock.remove_stock(form.quantity.data):
                    flash('Stok tidak mencukupi!', 'danger')
                    return render_template('stock/add.html', form=form)

            # Create transaction record
            transaction = StockTransaction(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data,
                transaction_type=form.transaction_type.data,
                quantity=form.quantity.data,
                note=form.note.data
            )
            transaction.save()

            flash('Transaksi stok berhasil!', 'success')
            return redirect(url_for('stock.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('stock/add.html', form=form, transaction_type='IN')


@bp.route('/remove', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def remove():
    """Remove stock transaction (OUT)"""
    form = StockTransactionForm()

    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    if current_user.is_warehouse_staff():
        # Get warehouses from UserWarehouse assignments (many-to-many)
        user_warehouses = current_user.user_warehouses.all()
        if user_warehouses:
            form.warehouse_id.choices = [(uw.warehouse.id, uw.warehouse.name) for uw in user_warehouses]
        else:
            form.warehouse_id.choices = []
    else:
        form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    if form.validate_on_submit():
        try:
            stock = Stock.query.filter_by(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data
            ).first()

            if not stock:
                flash('Stok tidak ditemukan!', 'danger')
                return render_template('stock/remove.html', form=form)

            # Remove stock
            if not stock.remove_stock(form.quantity.data):
                flash('Stok tidak mencukupi!', 'danger')
                return render_template('stock/remove.html', form=form)

            # Create transaction record
            transaction = StockTransaction(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data,
                transaction_type=form.transaction_type.data,
                quantity=form.quantity.data,
                note=form.note.data
            )
            transaction.save()

            flash('Transaksi stok berhasil!', 'success')
            return redirect(url_for('stock.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('stock/remove.html', form=form, transaction_type='OUT')


@bp.route('/low-stock')
@login_required
def low_stock():
    """Show low stock items"""
    threshold = request.args.get('threshold', 10, type=int)
    low_stocks = Stock.query.filter(Stock.quantity < threshold).all()

    return render_template('stock/low_stock.html', low_stocks=low_stocks, threshold=threshold)


@bp.route('/transactions')
@login_required
def transactions():
    """Show stock transaction history"""
    if current_user.is_warehouse_staff():
        # Get warehouse IDs from UserWarehouse assignments (many-to-many)
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            transactions = StockTransaction.query.filter(StockTransaction.warehouse_id.in_(user_warehouse_ids)).order_by(StockTransaction.transaction_date.desc()).all()
        else:
            transactions = []
    else:
        transactions = StockTransaction.query.order_by(StockTransaction.transaction_date.desc()).all()

    return render_template('stock/transactions.html', transactions=transactions)


@bp.route('/item/<int:item_id>')
@login_required
def item_stock(item_id):
    """Show stock for specific item across warehouses"""
    item = Item.query.get_or_404(item_id)
    stocks = Stock.query.filter_by(item_id=item_id).all()

    return render_template('stock/item_stock.html', item=item, stocks=stocks)
