from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import Item, ItemDetail, Category

bp = Blueprint('api_items', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all items"""
    items = Item.query.all()
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })


@bp.route('/categories')
@login_required
def api_categories():
    """Get all categories"""
    categories = Category.query.all()
    return jsonify({
        'success': True,
        'categories': [cat.to_dict() for cat in categories]
    })


@bp.route('/<int:id>')
@login_required
def api_detail(id):
    """Get item detail"""
    item = Item.query.get_or_404(id)
    return jsonify({
        'success': True,
        'item': item.to_dict()
    })


@bp.route('/<int:id>/item-details')
@login_required
def api_item_details(id):
    """Get item details (serial numbers) for item"""
    item_details = ItemDetail.query.filter_by(item_id=id).all()
    return jsonify({
        'success': True,
        'item_details': [detail.to_dict() for detail in item_details]
    })


@bp.route('/search')
@login_required
def api_search():
    """Search items"""
    from flask import request
    query = request.args.get('q', '')

    items = Item.query.filter(
        db.or_(
            Item.name.ilike(f'%{query}%'),
            Item.item_code.ilike(f'%{query}%')
        )
    ).all()

    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items]
    })
