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
    """Stock history page - only warehouse stock transactions"""
    # Unified list of all transactions (individual items)
    all_entries = []

    # Helper function to get timestamp for sorting
    def get_timestamp(entry):
        return entry.get('timestamp')

    # 1. StockTransaction IN (bukan dari procurement)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            trans_in = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'IN',
                ~StockTransaction.note.like('%Procurement%'),
                ~StockTransaction.note.like('%Pengadaan%')
            ).order_by(StockTransaction.transaction_date.desc()).limit(100).all()
        else:
            trans_in = []
    else:
        trans_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            ~StockTransaction.note.like('%Procurement%'),
            ~StockTransaction.note.like('%Pengadaan%')
        ).order_by(StockTransaction.transaction_date.desc()).limit(100).all()

    for trans in trans_in:
        all_entries.append({
            'type': 'stock_in',
            'timestamp': trans.transaction_date,
            'data': trans
        })

    # 2. StockTransaction OUT (bukan dari procurement)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            trans_out = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'OUT',
                ~StockTransaction.note.like('%Procurement%'),
                ~StockTransaction.note.like('%Pengadaan%')
            ).order_by(StockTransaction.transaction_date.desc()).limit(100).all()
        else:
            trans_out = []
    else:
        trans_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            ~StockTransaction.note.like('%Procurement%'),
            ~StockTransaction.note.like('%Pengadaan%')
        ).order_by(StockTransaction.transaction_date.desc()).limit(100).all()

    for trans in trans_out:
        all_entries.append({
            'type': 'stock_out',
            'timestamp': trans.transaction_date,
            'data': trans
        })

    # 3. ReturnBatch - per item
    from app.models.return_batch import ReturnBatch
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            return_batches = ReturnBatch.query.filter(
                ReturnBatch.warehouse_id.in_(user_warehouse_ids),
                ReturnBatch.status == 'confirmed'
            ).order_by(ReturnBatch.confirmed_at.desc()).limit(50).all()
        else:
            return_batches = []
    else:
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed'
        ).order_by(ReturnBatch.confirmed_at.desc()).limit(50).all()

    for batch in return_batches:
        timestamp = batch.confirmed_at if batch.confirmed_at else batch.created_at
        for item in batch.return_items:
            all_entries.append({
                'type': 'return_batch',
                'timestamp': timestamp,
                'data': (batch, item)
            })

    # 4. Procurement - per item
    from app.models.procurement import Procurement
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            procurements = Procurement.query.filter(
                Procurement.warehouse_id.in_(user_warehouse_ids),
                Procurement.status == 'completed'
            ).order_by(Procurement.completion_date.desc()).limit(50).all()
        else:
            procurements = []
    else:
        procurements = Procurement.query.filter(
            Procurement.status == 'completed'
        ).order_by(Procurement.completion_date.desc()).limit(50).all()

    for proc in procurements:
        timestamp = proc.completion_date if proc.completion_date else proc.created_at
        for item in proc.items:
            all_entries.append({
                'type': 'procurement',
                'timestamp': timestamp,
                'data': (proc, item)
            })

    # 5. DistributionGroup - per item
    from app.models.distribution_group import DistributionGroup
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            distribution_groups = DistributionGroup.query.filter(
                DistributionGroup.warehouse_id.in_(user_warehouse_ids),
                DistributionGroup.status.in_(['approved', 'distributed'])
            ).order_by(DistributionGroup.verified_at.desc()).limit(50).all()
        else:
            distribution_groups = []
    else:
        distribution_groups = DistributionGroup.query.filter(
            DistributionGroup.status.in_(['approved', 'distributed'])
        ).order_by(DistributionGroup.verified_at.desc()).limit(50).all()

    for group in distribution_groups:
        timestamp = group.verified_at if group.verified_at else group.created_at
        for dist in group.distributions:
            all_entries.append({
                'type': 'distribution_group',
                'timestamp': timestamp,
                'data': (group, dist)
            })

    # 6. Direct Distribution - per item
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            direct_distributions = Distribution.query.filter(
                Distribution.warehouse_id.in_(user_warehouse_ids),
                Distribution.distribution_group_id == None,
                Distribution.status == 'installed'
            ).order_by(Distribution.created_at.desc()).limit(50).all()
        else:
            direct_distributions = []
    else:
        direct_distributions = Distribution.query.filter(
            Distribution.distribution_group_id == None,
            Distribution.status == 'installed'
        ).order_by(Distribution.created_at.desc()).limit(50).all()

    for dist in direct_distributions:
        all_entries.append({
            'type': 'direct_distribution',
            'timestamp': dist.created_at,
            'data': dist
        })

    # Sort all entries by timestamp (newest first)
    all_entries.sort(key=get_timestamp, reverse=True)

    return render_template('stock/index.html',
                         all_entries=all_entries)


@bp.route('/recap')
@login_required
def recap():
    """Annual recap/report page"""
    year = request.args.get('year', datetime.now().year, type=int)

    # Get stock transactions per month (exclude procurement to avoid duplication)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            stock_in = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'IN',
                ~StockTransaction.note.like('%Pengadaan%'),
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
            ~StockTransaction.note.like('%Pengadaan%'),
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

    # Get procurements (completed in selected year)
    from app.models.procurement import Procurement
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            procurements = Procurement.query.filter(
                Procurement.warehouse_id.in_(user_warehouse_ids),
                Procurement.status == 'completed',
                func.extract('year', Procurement.completion_date) == year
            ).all()
        else:
            procurements = []
    else:
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            func.extract('year', Procurement.completion_date) == year
        ).all()

    # Calculate procurement total
    total_procurement = sum(item.quantity for proc in procurements for item in proc.items)

    # Get return batches (confirmed in selected year)
    from app.models.return_batch import ReturnBatch
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            return_batches = ReturnBatch.query.filter(
                ReturnBatch.warehouse_id.in_(user_warehouse_ids),
                ReturnBatch.status == 'confirmed',
                func.extract('year', ReturnBatch.confirmed_at) == year
            ).all()
        else:
            return_batches = []
    else:
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            func.extract('year', ReturnBatch.confirmed_at) == year
        ).all()

    # Calculate return batch total
    total_return_batches = sum(len(batch.return_items) for batch in return_batches)

    # Calculate perolehan (total procured items)
    total_perolehan = total_procurement

    return render_template('stock/recap.html',
                         year=year,
                         now=datetime.now(),
                         total_in=total_in,
                         total_out=total_out,
                         total_distributed=total_distributed,
                         total_returned=total_returned,
                         total_obname=total_obname,
                         total_procurement=total_procurement,
                         total_return_batches=total_return_batches,
                         total_perolehan=total_perolehan,
                         in_by_source=in_by_source,
                         out_by_source=out_by_source,
                         stock_in=stock_in,
                         stock_out=stock_out,
                         distributions=distributions,
                         returns=returns,
                         obname_items=obname_items,
                         procurements=procurements,
                         return_batches=return_batches)


@bp.route('/per-unit')
@login_required
def per_unit():
    """Show list of all units with their stock summary"""
    from app.models import Unit
    from app.models.distribution import Distribution
    from app.models.master_data import ItemDetail

    # Get all active units
    units = Unit.query.filter_by(status='active').all()

    unit_summary = []
    for unit in units:
        # Get all distributions to this unit that are not rejected/returned
        distributions = Distribution.query.filter(
            Distribution.unit_id == unit.id,
            Distribution.status != 'rejected'
        ).all()

        # Get item details for this unit (excluding returned items)
        item_detail_ids = [d.item_detail_id for d in distributions if d.item_detail_id]

        if item_detail_ids:
            # Get item details and exclude returned ones
            item_details = ItemDetail.query.filter(
                ItemDetail.id.in_(item_detail_ids),
                ItemDetail.status != 'returned'
            ).all()

            # Count by item_detail status
            total_items = len(item_details)
            loaned_count = len([d for d in item_details if d.status == 'loaned'])
            used_count = len([d for d in item_details if d.status == 'used'])
        else:
            total_items = 0
            loaned_count = 0
            used_count = 0

        unit_summary.append({
            'unit': unit,
            'total_items': total_items,
            'loaned_count': loaned_count,
            'used_count': used_count
        })

    return render_template('stock/per_unit.html', unit_summary=unit_summary)


@bp.route('/per-unit/<int:unit_id>')
@login_required
def per_unit_detail(unit_id):
    """Show detailed stock for a specific unit (similar to unit-assets)"""
    from app.models import Unit
    from app.models.distribution import Distribution
    from app.models.master_data import ItemDetail
    from collections import defaultdict

    # Get the unit
    unit = Unit.query.get_or_404(unit_id)

    # Get all distributions to this unit (excluding rejected)
    distributions = Distribution.query.filter(
        Distribution.unit_id == unit_id,
        Distribution.status != 'rejected'
    ).all()

    # Get all item details for this unit (excluding returned items)
    item_detail_ids = [d.item_detail_id for d in distributions if d.item_detail_id]
    item_details = ItemDetail.query.filter(
        ItemDetail.id.in_(item_detail_ids),
        ItemDetail.status != 'returned'
    ).all() if item_detail_ids else []

    # Calculate stats
    in_unit_count = len([d for d in item_details if d.status == 'in_unit'])
    loaned_count = len([d for d in item_details if d.status == 'loaned'])
    used_count = len([d for d in item_details if d.status == 'used'])

    # Group items by item_id (only include items that are not returned)
    items_dict = defaultdict(lambda: {
        'item': None,
        'details': [],
        'total_quantity': 0
    })

    # Collect all items from distributions (excluding returned items)
    for dist in distributions:
        if dist.item_detail and dist.item_detail.item and dist.item_detail.status != 'returned':
            item_id = dist.item_detail.item_id
            items_dict[item_id]['item'] = dist.item_detail.item
            items_dict[item_id]['details'].append({
                'item_detail': dist.item_detail,
                'serial_number': dist.item_detail.serial_number,
                'distribution_date': dist.installed_at or dist.created_at,
                'location': f"{dist.unit_detail.room_name if dist.unit_detail else 'N/A'}",
                'status': dist.item_detail.status,
                'distribution_id': dist.id
            })
            items_dict[item_id]['total_quantity'] += 1

    # Sort items by name
    sorted_items = sorted(items_dict.values(), key=lambda x: x['item'].name if x['item'] else '')

    return render_template('stock/per_unit_detail.html',
                         unit=unit,
                         items=sorted_items,
                         total_items=len(item_details),
                         in_unit_count=in_unit_count,
                         loaned_count=loaned_count,
                         used_count=used_count)


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


@bp.route('/recap/pdf/<int:year>')
@login_required
def recap_pdf(year):
    """Generate PDF version of annual recap report"""
    # Get stock transactions per month (manual transactions only, exclude procurement)
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

    # Get procurements (completed in selected year)
    from app.models.procurement import Procurement
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            procurements = Procurement.query.filter(
                Procurement.warehouse_id.in_(user_warehouse_ids),
                Procurement.status == 'completed',
                func.extract('year', Procurement.completion_date) == year
            ).all()
        else:
            procurements = []
    else:
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            func.extract('year', Procurement.completion_date) == year
        ).all()

    # Calculate procurement total
    total_procurement = sum(item.quantity for proc in procurements for item in proc.items)

    # Get return batches (confirmed in selected year)
    from app.models.return_batch import ReturnBatch
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            return_batches = ReturnBatch.query.filter(
                ReturnBatch.warehouse_id.in_(user_warehouse_ids),
                ReturnBatch.status == 'confirmed',
                func.extract('year', ReturnBatch.confirmed_at) == year
            ).all()
        else:
            return_batches = []
    else:
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            func.extract('year', ReturnBatch.confirmed_at) == year
        ).all()

    # Calculate return batch total
    total_return_batches = sum(len(batch.return_items) for batch in return_batches)

    # Calculate perolehan (total procured items)
    total_perolehan = total_procurement

    return render_template('stock/recap_pdf.html',
                         year=year,
                         now=datetime.now(),
                         total_in=total_in,
                         total_out=total_out,
                         total_distributed=total_distributed,
                         total_returned=total_returned,
                         total_obname=total_obname,
                         total_procurement=total_procurement,
                         total_return_batches=total_return_batches,
                         total_perolehan=total_perolehan,
                         in_by_source=in_by_source,
                         out_by_source=out_by_source,
                         stock_in=stock_in,
                         stock_out=stock_out,
                         distributions=distributions,
                         returns=returns,
                         obname_items=obname_items,
                         procurements=procurements,
                         return_batches=return_batches)
