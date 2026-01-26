from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Distribution, ItemDetail, User, Unit, UnitDetail, AssetMovementLog
from app.utils.decorators import role_required
from app.utils.helpers import get_user_warehouse_id

bp = Blueprint('api_installations', __name__)


@bp.route('/')
@login_required
def api_list():
    """Get all installations"""
    if current_user.is_warehouse_staff():
        installations = Distribution.query.filter_by(warehouse_id=get_user_warehouse_id(current_user)).all()
    elif current_user.is_field_staff():
        installations = Distribution.query.filter_by(field_staff_id=current_user.id).all()
    else:
        installations = Distribution.query.all()

    return jsonify({
        'success': True,
        'installations': [inst.to_dict() for inst in installations]
    })


@bp.route('/create', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def api_create():
    """Create new installation via API"""
    data = request.get_json()

    try:
        item_detail = ItemDetail.query.get(data['item_detail_id'])
        if not item_detail or item_detail.status != 'available':
            return jsonify({'success': False, 'message': 'Item not available'}), 400

        distribution = Distribution(
            item_detail_id=data['item_detail_id'],
            warehouse_id=item_detail.warehouse_id,
            field_staff_id=data['field_staff_id'],
            unit_id=data['unit_id'],
            unit_detail_id=data['unit_detail_id'],
            address=data['address'],
            note=data.get('note', ''),
            status='installing'
        )

        if data.get('latitude') and data.get('longitude'):
            distribution.set_coordinates(data['latitude'], data['longitude'])

        distribution.save()

        # Update item status
        item_detail.status = 'processing'
        item_detail.save()

        # Log movement
        AssetMovementLog.log_movement(
            item_detail=item_detail,
            operator=current_user,
            origin_type='warehouse',
            origin_id=item_detail.warehouse_id,
            destination_type='unit',
            destination_id=data['unit_id'],
            status_before='available',
            status_after='processing',
            note=data.get('note', '')
        )

        return jsonify({
            'success': True,
            'message': 'Installation created successfully',
            'installation': distribution.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:id>/verify', methods=['POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def api_verify(id):
    """Verify installation completion"""
    distribution = Distribution.query.get_or_404(id)

    try:
        distribution.status = 'installed'
        distribution.save()

        item_detail = distribution.item_detail
        item_detail.status = 'used'
        item_detail.save()

        AssetMovementLog.log_movement(
            item_detail=item_detail,
            operator=current_user,
            origin_type='warehouse',
            origin_id=distribution.warehouse_id,
            destination_type='unit',
            destination_id=distribution.unit_id,
            status_before='processing',
            status_after='used',
            note='Installation verified'
        )

        return jsonify({
            'success': True,
            'message': 'Installation verified successfully'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:id>')
@login_required
def api_detail(id):
    """Get installation detail"""
    installation = Distribution.query.get_or_404(id)
    return jsonify({
        'success': True,
        'installation': installation.to_dict()
    })
