from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import UnitDetail, ItemDetail
from app.utils.decorators import role_required

bp = Blueprint('api_units', __name__, url_prefix='/api/unit-details')


@bp.route('/<int:unit_detail_id>/assets')
@login_required
@role_required('admin')
def get_unit_detail_assets(unit_detail_id):
    """Get all assets installed in a specific unit detail (room)"""
    try:
        unit_detail = UnitDetail.query.get_or_404(unit_detail_id)

        # Get all item details installed in this unit detail
        item_details = ItemDetail.query.filter_by(
            unit_detail_id=unit_detail_id
        ).all()

        assets = []
        for item_detail in item_details:
            if item_detail.item:
                assets.append({
                    'id': item_detail.id,
                    'item_name': item_detail.item.name,
                    'serial_number': item_detail.serial_number or 'N/A',
                    'status': item_detail.status,
                    'item_id': item_detail.item_id
                })

        return jsonify({
            'success': True,
            'unit_detail_id': unit_detail_id,
            'room_name': unit_detail.room_name or 'Ruangan Tanpa Nama',
            'assets': assets,
            'total_count': len(assets)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
