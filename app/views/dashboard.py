from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.helpers import get_dashboard_stats, get_user_warehouse_id
from sqlalchemy import func, extract
from datetime import datetime

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
    from app.models import AssetRequest, Warehouse
    from app.models.user import UserWarehouse
    from app.utils.helpers import get_warehouse_dashboard_stats

    # Get warehouse from UserWarehouse relationship
    warehouse_id = get_user_warehouse_id(current_user)

    if warehouse_id:
        warehouse = Warehouse.query.get(warehouse_id)
    else:
        warehouse = None

    # Get keyword-based stats for this warehouse
    stats = get_warehouse_dashboard_stats(warehouse_id) if warehouse_id else {}

    return render_template('dashboard/warehouse_index.html',
                         stats=stats,
                         warehouse=warehouse,
                         warehouse_id=warehouse_id,
                         user=current_user)


@bp.route('/admin')
@login_required
@role_required('admin')
def admin_index():
    """Admin dashboard"""
    from app.models import AssetRequest, UserUnit

    stats = get_dashboard_stats()

    # Jangan override pending_request_count, biarkan pakai context processor
    # Context processor sudah menghitung AssetRequest dengan status 'pending'

    return render_template('dashboard/admin_index.html',
                         stats=stats,
                         user=current_user)


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
    from app.models import Unit, UserUnit
    from app.utils.helpers import get_unit_dashboard_stats

    # Get only units assigned to current unit staff
    units = current_user.get_assigned_units()
    units_list = list(units)  # Convert query to list

    # Get unit IDs
    unit_ids = [u.id for u in units_list]

    # Get keyword-based stats for this unit's items
    stats = get_unit_dashboard_stats(unit_ids) if unit_ids else {}

    return render_template('dashboard/unit_index.html',
                         units=units_list,
                         stats=stats,
                         unit_ids=unit_ids,
                         user=current_user)


@bp.route('/api/stock-transactions')
@login_required
@role_required('admin')
def api_stock_transactions():
    """API for stock transaction chart data (including all sources like stock page)"""
    from app.models import (StockTransaction, DistributionGroup, Distribution,
                           ReturnBatch, Procurement, ProcurementItem)
    from app import db
    from sqlalchemy import func, extract

    filter_type = request.args.get('filter', 'month')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    # Build all entries list (like stock.py)
    all_entries = []

    if filter_type == 'month':
        # 1. StockTransaction IN (excluding procurement)
        stock_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            ~StockTransaction.note.like('%Pengadaan%'),
            extract('year', StockTransaction.transaction_date) == year,
            extract('month', StockTransaction.transaction_date) == month
        ).all()

        for trans in stock_in:
            all_entries.append({
                'type': 'in',
                'timestamp': trans.transaction_date,
                'quantity': trans.quantity
            })

        # 2. StockTransaction OUT (excluding procurement)
        stock_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            ~StockTransaction.note.like('%Pengadaan%'),
            extract('year', StockTransaction.transaction_date) == year,
            extract('month', StockTransaction.transaction_date) == month
        ).all()

        for trans in stock_out:
            all_entries.append({
                'type': 'out',
                'timestamp': trans.transaction_date,
                'quantity': trans.quantity
            })

        # 3. ReturnBatch (status='confirmed')
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            extract('year', ReturnBatch.confirmed_at) == year,
            extract('month', ReturnBatch.confirmed_at) == month
        ).all()

        for batch in return_batches:
            timestamp = batch.confirmed_at if batch.confirmed_at else batch.created_at
            for item in batch.return_items:
                all_entries.append({
                    'type': 'in',
                    'timestamp': timestamp,
                    'quantity': 1
                })

        # 4. Procurement (status='completed')
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            extract('year', Procurement.completion_date) == year,
            extract('month', Procurement.completion_date) == month
        ).all()

        for proc in procurements:
            timestamp = proc.completion_date if proc.completion_date else proc.created_at
            for item in proc.items:
                all_entries.append({
                    'type': 'in',
                    'timestamp': timestamp,
                    'quantity': item.quantity
                })

        # 5. DistributionGroup (barang keluar)
        distribution_groups = DistributionGroup.query.filter(
            DistributionGroup.status.in_(['approved', 'distributed']),
            extract('year', DistributionGroup.verified_at) == year,
            extract('month', DistributionGroup.verified_at) == month
        ).all()

        for group in distribution_groups:
            timestamp = group.verified_at if group.verified_at else group.created_at
            for dist in group.distributions:
                all_entries.append({
                    'type': 'out',
                    'timestamp': timestamp,
                    'quantity': 1
                })

        # 6. Direct Distribution (distribution_group_id=None, status='installed')
        direct_dists = Distribution.query.filter(
            Distribution.distribution_group_id == None,
            Distribution.status == 'installed',
            extract('year', Distribution.updated_at) == year,
            extract('month', Distribution.updated_at) == month
        ).all()

        for dist in direct_dists:
            all_entries.append({
                'type': 'out',
                'timestamp': dist.updated_at,
                'quantity': 1
            })

        # Aggregate by day
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        in_by_day = {day: 0 for day in range(1, days_in_month + 1)}
        out_by_day = {day: 0 for day in range(1, days_in_month + 1)}

        for entry in all_entries:
            day = entry['timestamp'].day
            if entry['type'] == 'in':
                in_by_day[day] += entry['quantity']
            else:
                out_by_day[day] += entry['quantity']

        data = {'labels': [], 'in': [], 'out': []}
        for day in range(1, days_in_month + 1):
            data['labels'].append(f'{day}')
            data['in'].append(in_by_day[day])
            data['out'].append(out_by_day[day])

    else:  # year
        # 1. StockTransaction IN (excluding procurement)
        stock_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            ~StockTransaction.note.like('%Pengadaan%'),
            extract('year', StockTransaction.transaction_date) == year
        ).all()

        for trans in stock_in:
            all_entries.append({
                'type': 'in',
                'timestamp': trans.transaction_date,
                'quantity': trans.quantity
            })

        # 2. StockTransaction OUT (excluding procurement)
        stock_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            ~StockTransaction.note.like('%Pengadaan%'),
            extract('year', StockTransaction.transaction_date) == year
        ).all()

        for trans in stock_out:
            all_entries.append({
                'type': 'out',
                'timestamp': trans.transaction_date,
                'quantity': trans.quantity
            })

        # 3. ReturnBatch (status='confirmed')
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            extract('year', ReturnBatch.confirmed_at) == year
        ).all()

        for batch in return_batches:
            timestamp = batch.confirmed_at if batch.confirmed_at else batch.created_at
            for item in batch.return_items:
                all_entries.append({
                    'type': 'in',
                    'timestamp': timestamp,
                    'quantity': 1
                })

        # 4. Procurement (status='completed')
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            extract('year', Procurement.completion_date) == year
        ).all()

        for proc in procurements:
            timestamp = proc.completion_date if proc.completion_date else proc.created_at
            for item in proc.items:
                all_entries.append({
                    'type': 'in',
                    'timestamp': timestamp,
                    'quantity': item.quantity
                })

        # 5. DistributionGroup (barang keluar)
        distribution_groups = DistributionGroup.query.filter(
            DistributionGroup.status.in_(['approved', 'distributed']),
            extract('year', DistributionGroup.verified_at) == year
        ).all()

        for group in distribution_groups:
            timestamp = group.verified_at if group.verified_at else group.created_at
            for dist in group.distributions:
                all_entries.append({
                    'type': 'out',
                    'timestamp': timestamp,
                    'quantity': 1
                })

        # 6. Direct Distribution (distribution_group_id=None, status='installed')
        direct_dists = Distribution.query.filter(
            Distribution.distribution_group_id == None,
            Distribution.status == 'installed',
            extract('year', Distribution.updated_at) == year
        ).all()

        for dist in direct_dists:
            all_entries.append({
                'type': 'out',
                'timestamp': dist.updated_at,
                'quantity': 1
            })

        # Aggregate by month
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        in_by_month = {i: 0 for i in range(1, 13)}
        out_by_month = {i: 0 for i in range(1, 13)}

        for entry in all_entries:
            month_num = entry['timestamp'].month
            if entry['type'] == 'in':
                in_by_month[month_num] += entry['quantity']
            else:
                out_by_month[month_num] += entry['quantity']

        data = {'labels': month_names, 'in': [], 'out': []}
        for month_num in range(1, 13):
            data['in'].append(in_by_month[month_num])
            data['out'].append(out_by_month[month_num])

    return jsonify(data)


@bp.route('/api/recent-transactions')
@login_required
@role_required('admin')
def api_recent_transactions():
    """API for recent stock transactions with distribution progress (like stock page)"""
    from app.models import (StockTransaction, DistributionGroup, Distribution,
                           ReturnBatch, Procurement, Item, Warehouse, Unit)
    from app import db
    from sqlalchemy import func

    all_entries = []

    # 1. StockTransaction IN (excluding procurement)
    trans_in = StockTransaction.query.filter(
        StockTransaction.transaction_type == 'IN',
        ~StockTransaction.note.like('%Pengadaan%')
    ).order_by(
        StockTransaction.transaction_date.desc()
    ).limit(10).all()

    for trans in trans_in:
        all_entries.append({
            'type': 'stock_in',
            'timestamp': trans.transaction_date,
            'data': trans
        })

    # 2. ReturnBatch - per item
    return_batches = ReturnBatch.query.filter(
        ReturnBatch.status == 'confirmed'
    ).order_by(
        ReturnBatch.confirmed_at.desc()
    ).limit(10).all()

    for batch in return_batches:
        timestamp = batch.confirmed_at if batch.confirmed_at else batch.created_at
        for item in batch.return_items:
            all_entries.append({
                'type': 'return_batch',
                'timestamp': timestamp,
                'data': (batch, item)
            })

    # 3. Procurement - per item
    procurements = Procurement.query.filter(
        Procurement.status == 'completed'
    ).order_by(
        Procurement.completion_date.desc()
    ).limit(10).all()

    for proc in procurements:
        timestamp = proc.completion_date if proc.completion_date else proc.created_at
        for item in proc.items:
            all_entries.append({
                'type': 'procurement',
                'timestamp': timestamp,
                'data': (proc, item)
            })

    # 4. DistributionGroup - per item (Barang Keluar)
    distribution_groups = DistributionGroup.query.filter(
        DistributionGroup.status.in_(['approved', 'distributed'])
    ).order_by(
        DistributionGroup.verified_at.desc()
    ).limit(10).all()

    for group in distribution_groups:
        timestamp = group.verified_at if group.verified_at else group.created_at
        for dist in group.distributions:
            all_entries.append({
                'type': 'distribution_group',
                'timestamp': timestamp,
                'data': (group, dist)
            })

    # 5. Direct Distribution - per item (distribution_group_id=None, status='installed')
    direct_dists = Distribution.query.filter(
        Distribution.distribution_group_id == None,
        Distribution.status == 'installed'
    ).order_by(
        Distribution.updated_at.desc()
    ).limit(10).all()

    for dist in direct_dists:
        timestamp = dist.updated_at
        all_entries.append({
            'type': 'direct_distribution',
            'timestamp': timestamp,
            'data': dist
        })

    # Sort by timestamp
    all_entries.sort(key=lambda x: x['timestamp'], reverse=True)

    # Build response data (first 10)
    data = []

    for entry in all_entries[:10]:
        if entry['type'] == 'stock_in':
            # StockTransaction IN
            trans = entry['data']
            item = Item.query.get(trans.item_id)
            warehouse = Warehouse.query.get(trans.warehouse_id)

            data.append({
                'id': f'stin_{trans.id}',
                'type': 'IN',
                'item_name': item.name if item else 'Unknown',
                'item_code': item.item_code if item else '',
                'quantity': trans.quantity,
                'date': trans.transaction_date.strftime('%d/%m/%Y %H:%M'),
                'warehouse_name': warehouse.name if warehouse else 'Unknown',
                'note': trans.note or ''
            })

        elif entry['type'] == 'return_batch':
            # ReturnBatch
            batch, item = entry['data']
            item_detail = item.item_detail
            item_obj = item_detail.item if item_detail else None
            warehouse = batch.warehouse

            data.append({
                'id': f'ret_{batch.id}_{item.id}',
                'type': 'IN',
                'item_name': item_obj.name if item_obj else 'Unknown',
                'item_code': item_obj.item_code if item_obj else '',
                'quantity': 1,
                'date': (batch.confirmed_at if batch.confirmed_at else batch.created_at).strftime('%d/%m/%Y %H:%M'),
                'warehouse_name': warehouse.name if warehouse else 'Unknown',
                'note': 'Kembali'
            })

        elif entry['type'] == 'procurement':
            # Procurement
            proc, item = entry['data']
            item_obj = item.item if item else None
            warehouse = proc.warehouse

            data.append({
                'id': f'proc_{proc.id}_{item.id}',
                'type': 'IN',
                'item_name': item_obj.name if item_obj else 'Unknown',
                'item_code': item_obj.item_code if item_obj else '',
                'quantity': item.quantity,
                'date': (proc.completion_date if proc.completion_date else proc.created_at).strftime('%d/%m/%Y %H:%M'),
                'warehouse_name': warehouse.name if warehouse else 'Unknown',
                'note': f'Pengadaan #{proc.id}'
            })

        elif entry['type'] == 'distribution_group':
            # DistributionGroup (Barang Keluar)
            group, dist = entry['data']
            item_detail = dist.item_detail
            item_obj = item_detail.item if item_detail else None
            warehouse = group.warehouse
            unit = dist.unit if hasattr(dist, 'unit') else None

            data.append({
                'id': f'dist_{group.id}_{dist.id}',
                'type': 'OUT',
                'item_name': item_obj.name if item_obj else 'Unknown',
                'item_code': item_obj.item_code if item_obj else '',
                'quantity': 1,
                'date': (group.verified_at if group.verified_at else group.created_at).strftime('%d/%m/%Y %H:%M'),
                'warehouse_name': warehouse.name if warehouse else 'Unknown',
                'unit_name': unit.name if unit else '',
                'note': 'Distribusi'
            })

        elif entry['type'] == 'direct_distribution':
            # Direct Distribution (Barang Keluar - Permintaan)
            dist = entry['data']
            item_detail = dist.item_detail
            item_obj = item_detail.item if item_detail else None
            warehouse = dist.warehouse if hasattr(dist, 'warehouse') else None
            unit = dist.unit if hasattr(dist, 'unit') else None

            data.append({
                'id': f'direct_{dist.id}',
                'type': 'OUT',
                'item_name': item_obj.name if item_obj else 'Unknown',
                'item_code': item_obj.item_code if item_obj else '',
                'quantity': 1,
                'date': dist.updated_at.strftime('%d/%m/%Y %H:%M'),
                'warehouse_name': warehouse.name if warehouse else '-',
                'unit_name': unit.name if unit else '',
                'note': 'Permintaan'
            })

    return jsonify(data)


def get_transaction_type_badge(tx_type):
    """Get transaction type badge HTML"""
    if tx_type == 'IN':
        return '<span class="px-2 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-semibold">Barang Masuk</span>'
    else:
        return '<span class="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">Barang Keluar</span>'


def get_group_status_badge(status):
    """Get distribution group status badge HTML"""
    badges = {
        'pending': '<span class="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-semibold">Pending</span>',
        'approved': '<span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">Disetujui</span>',
        'in_transit': '<span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">Dalam Perjalanan</span>',
        'installing': '<span class="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold">Sedang Dipasang</span>',
        'installed': '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">Terpasang</span>',
        'completed': '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">Selesai</span>',
        'cancelled': '<span class="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">Dibatalkan</span>'
    }
    return badges.get(status, '<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">{}</span>'.format(status))


def get_status_badge(status):
    """Get status badge HTML"""
    badges = {
        'pending': '<span class="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-semibold">Pending</span>',
        'in_transit': '<span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">Dalam Perjalanan</span>',
        'installing': '<span class="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold">Sedang Dipasang</span>',
        'installed': '<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">Terpasang</span>',
        'broken': '<span class="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">Rusak</span>',
        'returned': '<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">Dikembalikan</span>'
    }
    return badges.get(status, '<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">{}</span>'.format(status))


@bp.route('/api/unit/received-batches')
@login_required
@role_required('unit_staff')
def api_unit_received_batches():
    """API for received distribution batches (barang diterima oleh unit)"""
    from app.models import Distribution, DistributionGroup, Warehouse

    # Get user's assigned unit IDs
    unit_ids = [uu.unit_id for uu in current_user.user_units]

    # Get completed distribution groups (batches) for user's units (like receive_history)
    completed_groups = DistributionGroup.query.filter(
        DistributionGroup.is_draft == False,
        DistributionGroup.status == 'approved',
        DistributionGroup.verification_received_at.isnot(None)
    ).join(Distribution).filter(
        Distribution.unit_id.in_(unit_ids),
        Distribution.verification_status == 'submitted'
    ).distinct().order_by(DistributionGroup.verification_received_at.desc()).limit(3).all()

    # Build history data (like receive_history)
    history_list = []
    for group in completed_groups:
        # Get all completed distributions for this batch and user's units
        batch_distributions = Distribution.query.filter(
            Distribution.distribution_group_id == group.id,
            Distribution.unit_id.in_(unit_ids),
            Distribution.verification_status == 'submitted'
        ).all()

        if batch_distributions:
            # Get warehouse from first distribution
            warehouse = None
            if batch_distributions and batch_distributions[0].distribution_group:
                warehouse = batch_distributions[0].distribution_group.warehouse

            history_list.append({
                'id': group.id,
                'batch_code': group.batch_code,
                'warehouse_name': warehouse.name if warehouse else 'Unknown',
                'total_items': len(batch_distributions),
                'received_at': group.verification_received_at.strftime('%d/%m/%Y %H:%M') if group.verification_received_at else '',
                'has_photo': batch_distributions[0].distribution_group.verification_photo is not None if batch_distributions else False,
                'first_dist_id': batch_distributions[0].id if batch_distributions else None
            })

    return jsonify(history_list)


@bp.route('/api/unit/received-chart')
@login_required
@role_required('unit_staff')
def api_unit_received_chart():
    """API for received items chart data (grafik jumlah penerimaan barang)"""
    from app.models import Distribution, DistributionGroup
    from app import db
    from sqlalchemy import extract

    # Get user's assigned unit IDs
    unit_ids = [uu.unit_id for uu in current_user.user_units]

    filter_type = request.args.get('filter', 'month')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    if filter_type == 'month':
        # Get received distributions by day
        received_by_day = db.session.query(
            extract('day', DistributionGroup.verification_received_at).label('day'),
            func.count(Distribution.id).label('total')
        ).filter(
            DistributionGroup.is_draft == False,
            DistributionGroup.status == 'approved',
            DistributionGroup.verification_received_at.isnot(None)
        ).join(
            Distribution, DistributionGroup.id == Distribution.distribution_group_id
        ).filter(
            Distribution.unit_id.in_(unit_ids),
            Distribution.verification_status == 'submitted',
            extract('year', DistributionGroup.verification_received_at) == year,
            extract('month', DistributionGroup.verification_received_at) == month
        ).group_by(
            extract('day', DistributionGroup.verification_received_at)
        ).all()

        import calendar
        days_in_month = calendar.monthrange(year, month)[1]

        data = {'labels': [], 'received': []}
        for day in range(1, days_in_month + 1):
            data['labels'].append(f'{day}')
            qty = next((r.total for r in received_by_day if r.day == day), 0)
            data['received'].append(qty or 0)

    else:  # year
        # Get received distributions by month
        received_by_month = db.session.query(
            extract('month', DistributionGroup.verification_received_at).label('month'),
            func.count(Distribution.id).label('total')
        ).filter(
            DistributionGroup.is_draft == False,
            DistributionGroup.status == 'approved',
            DistributionGroup.verification_received_at.isnot(None)
        ).join(
            Distribution, DistributionGroup.id == Distribution.distribution_group_id
        ).filter(
            Distribution.unit_id.in_(unit_ids),
            Distribution.verification_status == 'submitted',
            extract('year', DistributionGroup.verification_received_at) == year
        ).group_by(
            extract('month', DistributionGroup.verification_received_at)
        ).all()

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        data = {'labels': month_names, 'received': []}

        for month_num in range(1, 13):
            qty = next((r.total for r in received_by_month if r.month == month_num), 0)
            data['received'].append(qty or 0)

    return jsonify(data)


@bp.route('/api/warehouse/comparison-chart')
@login_required
@role_required('warehouse_staff')
def api_warehouse_comparison_chart():
    """API for procurement vs direct distribution comparison chart"""
    from app.models import Procurement, ProcurementItem, Distribution
    from app import db
    from sqlalchemy import extract

    # Get user's warehouse ID
    warehouse_id = get_user_warehouse_id(current_user)

    filter_type = request.args.get('filter', 'month')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    if filter_type == 'month':
        # Procurement (completed) by day
        procurement_by_day = db.session.query(
            extract('day', Procurement.completion_date).label('day'),
            func.sum(ProcurementItem.quantity).label('total')
        ).filter(
            Procurement.status == 'completed',
            Procurement.warehouse_id == warehouse_id,
            extract('year', Procurement.completion_date) == year,
            extract('month', Procurement.completion_date) == month
        ).join(
            ProcurementItem, Procurement.id == ProcurementItem.procurement_id
        ).group_by(
            extract('day', Procurement.completion_date)
        ).all()

        # Direct Distribution (like active_batches in installations) by day
        # Criteria: is_draft==False, draft_rejected==False, asset_request_id==None, draft_verified_at is not None
        dist_by_day = db.session.query(
            extract('day', Distribution.draft_verified_at).label('day'),
            func.count(Distribution.id).label('total')
        ).filter(
            Distribution.is_draft == False,
            Distribution.draft_rejected == False,
            Distribution.asset_request_id == None,
            Distribution.draft_verified_at.isnot(None),
            Distribution.warehouse_id == warehouse_id,
            extract('year', Distribution.draft_verified_at) == year,
            extract('month', Distribution.draft_verified_at) == month
        ).group_by(
            extract('day', Distribution.draft_verified_at)
        ).all()

        import calendar
        days_in_month = calendar.monthrange(year, month)[1]

        data = {'labels': [], 'procurement': [], 'distribution': []}
        for day in range(1, days_in_month + 1):
            data['labels'].append(f'{day}')
            proc_qty = next((r.total for r in procurement_by_day if r.day == day), 0)
            dist_qty = next((r.total for r in dist_by_day if r.day == day), 0)
            data['procurement'].append(proc_qty or 0)
            data['distribution'].append(dist_qty or 0)

    else:  # year
        # Procurement (completed) by month
        procurement_by_month = db.session.query(
            extract('month', Procurement.completion_date).label('month'),
            func.sum(ProcurementItem.quantity).label('total')
        ).filter(
            Procurement.status == 'completed',
            Procurement.warehouse_id == warehouse_id,
            extract('year', Procurement.completion_date) == year
        ).join(
            ProcurementItem, Procurement.id == ProcurementItem.procurement_id
        ).group_by(
            extract('month', Procurement.completion_date)
        ).all()

        # Direct Distribution (like active_batches in installations) by month
        dist_by_month = db.session.query(
            extract('month', Distribution.draft_verified_at).label('month'),
            func.count(Distribution.id).label('total')
        ).filter(
            Distribution.is_draft == False,
            Distribution.draft_rejected == False,
            Distribution.asset_request_id == None,
            Distribution.draft_verified_at.isnot(None),
            Distribution.warehouse_id == warehouse_id,
            extract('year', Distribution.draft_verified_at) == year
        ).group_by(
            extract('month', Distribution.draft_verified_at)
        ).all()

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        data = {'labels': month_names, 'procurement': [], 'distribution': []}

        for month_num in range(1, 13):
            proc_qty = next((r.total for r in procurement_by_month if r.month == month_num), 0)
            dist_qty = next((r.total for r in dist_by_month if r.month == month_num), 0)
            data['procurement'].append(proc_qty or 0)
            data['distribution'].append(dist_qty or 0)

    return jsonify(data)


@bp.route('/api/warehouse/recent-requests')
@login_required
@role_required('warehouse_staff')
def api_warehouse_recent_requests():
    """API for recent asset requests (permintaan unit terakhir)"""
    from app.models import AssetRequest, AssetRequestItem
    from sqlalchemy.orm import joinedload

    # For warehouse staff, only show requests with these statuses (like asset_requests/index)
    # Warehouse staff can see: verified (ready to distribute), distributing (in process), completed (done)
    try:
        requests = AssetRequest.query.options(
            joinedload(AssetRequest.unit),
            joinedload(AssetRequest.items)
        ).filter(
            AssetRequest.status.in_(['verified', 'distributing', 'completed'])
        ).order_by(
            AssetRequest.created_at.desc()
        ).limit(3).all()

        data = []
        for req in requests:
            # Translate status
            status_map = {
                'pending': 'Menunggu',
                'verified': 'Sudah Dicek',
                'distributing': 'Sedang Dikirim',
                'completed': 'Selesai',
                'rejected': 'Ditolak'
            }

            status_color_map = {
                'pending': 'bg-amber-100 text-amber-700',
                'verified': 'bg-indigo-100 text-indigo-700',
                'distributing': 'bg-blue-100 text-blue-700',
                'completed': 'bg-green-100 text-green-700',
                'rejected': 'bg-red-100 text-red-700'
            }

            data.append({
                'id': req.id,
                'request_date': req.request_date.strftime('%d/%m/%Y') if req.request_date else '-',
                'unit_name': req.unit.name if req.unit else '-',
                'items_count': len(req.items) if req.items else 0,
                'status': req.status,
                'status_display': status_map.get(req.status, req.status),
                'status_color': status_color_map.get(req.status, 'bg-gray-100 text-gray-700')
            })

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

