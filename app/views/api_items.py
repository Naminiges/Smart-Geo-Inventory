from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import Item, ItemDetail, Category
from app import db
from app.utils.pagination_helpers import paginated_response
from app.utils.cache_helpers import cache_frequently_accessed

bp = Blueprint('api_items', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all items with pagination"""
    from sqlalchemy import or_

    # Get base query
    query = Item.query

    # Apply search filter if provided
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            or_(
                Item.name.ilike(f'%{search}%'),
                Item.item_code.ilike(f'%{search}%')
            )
        )

    # Filter by category if provided
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)

    # Apply eager loading for better performance
    query = query.options(db.joinedload(Item.category))

    # Return paginated response
    return jsonify(paginated_response(query, max_per_page=100))


@bp.route('/categories')
@login_required
@cache_frequently_accessed(timeout=300)  # Cache for 5 minutes
def api_categories():
    """Get all categories (cached)"""
    categories = Category.query.all()
    return jsonify({
        'success': True,
        'categories': [cat.to_dict() for cat in categories]
    })


@bp.route('/<int:id>')
@login_required
def api_detail(id):
    """Get item detail"""
    item = Item.query.options(db.joinedload(Item.category)).get_or_404(id)
    return jsonify({
        'success': True,
        'item': item.to_dict()
    })


@bp.route('/<int:id>/item-details')
@login_required
def api_item_details(id):
    """Get item details (serial numbers) for item with pagination"""
    # Get base query
    query = ItemDetail.query.filter_by(item_id=id)

    # Apply eager loading
    query = query.options(
        db.joinedload(ItemDetail.item),
        db.joinedload(ItemDetail.warehouse)
    )

    # Return paginated response
    return jsonify(paginated_response(query, max_per_page=100))


@bp.route('/search')
@login_required
def api_search():
    """Search items with pagination"""
    from sqlalchemy import or_

    search = request.args.get('q', '')
    if not search:
        return jsonify({
            'success': False,
            'message': 'Search query is required'
        }), 400

    # Build search query with eager loading
    query = Item.query.filter(
        or_(
            Item.name.ilike(f'%{search}%'),
            Item.item_code.ilike(f'%{search}%')
        )
    ).options(db.joinedload(Item.category))

    # Return paginated response
    return jsonify(paginated_response(query, max_per_page=100))
