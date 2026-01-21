from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockTransaction, Item
from app.utils.decorators import role_required

bp = Blueprint('api_stock', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all stock"""
    if current_user.is_warehouse_staff():
        # Get warehouse IDs from UserWarehouse assignments (many-to-many)
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            stocks = Stock.query.filter(Stock.warehouse_id.in_(user_warehouse_ids)).all()
        else:
            stocks = []
    else:
        stocks = Stock.query.all()

    return jsonify({
        'success': True,
        'stocks': [stock.to_dict() for stock in stocks]
    })


@bp.route('/transaction', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def api_transaction():
    """Create stock transaction"""
    data = request.get_json()

    try:
        # Get or create stock
        stock = Stock.query.filter_by(
            item_id=data['item_id'],
            warehouse_id=data['warehouse_id']
        ).first()

        if not stock:
            stock = Stock(
                item_id=data['item_id'],
                warehouse_id=data['warehouse_id'],
                quantity=0
            )
            stock.save()

        # Process transaction
        if data['transaction_type'] == 'IN':
            stock.add_stock(data['quantity'])
        else:
            if not stock.remove_stock(data['quantity']):
                return jsonify({'success': False, 'message': 'Insufficient stock'}), 400

        # Create transaction record
        transaction = StockTransaction(
            item_id=data['item_id'],
            warehouse_id=data['warehouse_id'],
            transaction_type=data['transaction_type'],
            quantity=data['quantity'],
            note=data.get('note', '')
        )
        transaction.save()

        return jsonify({
            'success': True,
            'message': 'Transaction successful',
            'stock': stock.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/low-stock')
@login_required
def api_low_stock():
    """Get low stock items"""
    threshold = request.args.get('threshold', 10, type=int)
    low_stocks = Stock.query.filter(Stock.quantity < threshold).all()

    return jsonify({
        'success': True,
        'low_stocks': [stock.to_dict() for stock in low_stocks]
    })


@bp.route('/transactions')
@login_required
def api_transactions():
    """Get transaction history"""
    if current_user.is_warehouse_staff():
        # Get warehouse IDs from UserWarehouse assignments (many-to-many)
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            transactions = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids)
            ).order_by(StockTransaction.transaction_date.desc()).limit(100).all()
        else:
            transactions = []
    else:
        transactions = StockTransaction.query.order_by(
            StockTransaction.transaction_date.desc()
        ).limit(100).all()

    return jsonify({
        'success': True,
        'transactions': [t.to_dict() for t in transactions]
    })


@bp.route('/item/<int:item_id>')
@login_required
def api_item_stock(item_id):
    """Get stock for specific item"""
    stocks = Stock.query.filter_by(item_id=item_id).all()

    return jsonify({
        'success': True,
        'stocks': [stock.to_dict() for stock in stocks]
    })
