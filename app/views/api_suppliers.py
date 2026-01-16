from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import Supplier
from app.utils.decorators import role_required

bp = Blueprint('api_suppliers', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all suppliers"""
    suppliers = Supplier.query.all()
    return jsonify({
        'success': True,
        'suppliers': [supplier.to_dict() for supplier in suppliers]
    })


@bp.route('/create', methods=['POST'])
@login_required
@role_required('admin')
def api_create():
    """Create supplier via API"""
    data = request.get_json()

    try:
        supplier = Supplier(
            name=data['name'],
            contact_person=data.get('contact_person', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', '')
        )
        supplier.save()

        return jsonify({
            'success': True,
            'message': 'Supplier created successfully',
            'supplier': supplier.to_dict()
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:id>')
@login_required
def api_detail(id):
    """Get supplier detail"""
    supplier = Supplier.query.get_or_404(id)
    return jsonify({
        'success': True,
        'supplier': supplier.to_dict()
    })
