from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockTransaction, Item, Warehouse
from app.forms import StockForm, StockTransactionForm
from app.utils.decorators import role_required, warehouse_access_required
from sqlalchemy import func

bp = Blueprint('stock', __name__, url_prefix='/stock')


@bp.route('/')
@login_required
@warehouse_access_required
def index():
    """List all stock"""
    from app.models.user import UserWarehouse

    if current_user.is_warehouse_staff():
        # Get warehouse IDs from UserWarehouse assignments (many-to-many)
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            stocks = Stock.query.filter(Stock.warehouse_id.in_(user_warehouse_ids)).all()
        else:
            stocks = []
    else:
        stocks = Stock.query.all()

    return render_template('stock/index.html', stocks=stocks)


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
