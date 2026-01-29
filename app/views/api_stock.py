from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockTransaction, Item
from app.utils.decorators import role_required
from app.utils.pagination_helpers import paginated_response
from app.utils.cache_helpers import get_user_warehouse_ids

bp = Blueprint('api_stock', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all stock with pagination"""
    # Get base query
    query = Stock.query

    # Filter by user's warehouse access
    if current_user.is_warehouse_staff():
        user_warehouse_ids = get_user_warehouse_ids(current_user)
        if user_warehouse_ids:
            query = query.filter(Stock.warehouse_id.in_(user_warehouse_ids))
        else:
            query = query.filter(Stock.warehouse_id == -1)  # Return empty

    # Apply eager loading for better performance
    query = query.options(
        db.joinedload(Stock.item),
        db.joinedload(Stock.warehouse)
    )

    # Return paginated response
    return jsonify(paginated_response(query, max_per_page=100))


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
    """Get transaction history with pagination"""
    # Get base query
    query = StockTransaction.query

    # Filter by user's warehouse access
    if current_user.is_warehouse_staff():
        user_warehouse_ids = get_user_warehouse_ids(current_user)
        if user_warehouse_ids:
            query = query.filter(StockTransaction.warehouse_id.in_(user_warehouse_ids))
        else:
            query = query.filter(StockTransaction.warehouse_id == -1)  # Return empty

    # Order by date descending (newest first)
    query = query.order_by(StockTransaction.transaction_date.desc())

    # Apply eager loading
    query = query.options(
        db.joinedload(StockTransaction.item),
        db.joinedload(StockTransaction.warehouse)
    )

    # Return paginated response
    return jsonify(paginated_response(query, max_per_page=100))


@bp.route('/item/<int:item_id>')
@login_required
def api_item_stock(item_id):
    """Get stock for specific item"""
    query = Stock.query.filter_by(item_id=item_id)

    # Apply eager loading
    query = query.options(
        db.joinedload(Stock.item),
        db.joinedload(Stock.warehouse)
    )

    return jsonify(paginated_response(query, max_per_page=100))
