from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import UnitDetail, ItemDetail, Distribution
from app.utils.decorators import role_required
from collections import defaultdict

bp = Blueprint('api_units', __name__, url_prefix='/api/unit-details')


@bp.route('/<int:unit_detail_id>/assets')
@login_required
@role_required('admin')
def get_unit_detail_assets(unit_detail_id):
    """Get all assets installed in a specific unit detail (room)"""
    try:
        unit_detail = UnitDetail.query.get_or_404(unit_detail_id)

        # Get all distributions to this specific room (unit_detail)
        distributions = Distribution.query.filter(
            Distribution.unit_detail_id == unit_detail_id,
            Distribution.status != 'rejected'
        ).all()

        # Get item details from distributions
        assets = []
        for dist in distributions:
            if dist.item_detail and dist.item_detail.status != 'returned':
                item_detail = dist.item_detail
                if item_detail.item:
                    assets.append({
                        'id': item_detail.id,
                        'item_name': item_detail.item.name,
                        'item_code': item_detail.item.item_code or 'N/A',
                        'serial_number': item_detail.serial_number or 'N/A',
                        'serial_unit': item_detail.serial_unit or 'N/A',
                        'status': item_detail.status,
                        'item_id': item_detail.item_id,
                        'category_name': item_detail.item.category.name if item_detail.item.category else 'N/A',
                        'distribution_date': dist.installed_at.strftime('%d/%m/%Y') if dist.installed_at else '-'
                    })

        # Group by item for better display
        items_dict = defaultdict(lambda: {
            'item_name': '',
            'item_code': '',
            'category_name': '',
            'details': []
        })

        for asset in assets:
            item_id = asset['item_id']
            items_dict[item_id]['item_name'] = asset['item_name']
            items_dict[item_id]['item_code'] = asset['item_code']
            items_dict[item_id]['category_name'] = asset['category_name']
            items_dict[item_id]['details'].append({
                'serial_number': asset['serial_number'],
                'serial_unit': asset['serial_unit'],
                'status': asset['status'],
                'distribution_date': asset['distribution_date']
            })

        # Convert to list
        grouped_assets = []
        for item_id, data in items_dict.items():
            grouped_assets.append({
                'item_id': item_id,
                'item_name': data['item_name'],
                'item_code': data['item_code'],
                'category_name': data['category_name'],
                'total_quantity': len(data['details']),
                'details': data['details']
            })

        # Sort by item name
        grouped_assets.sort(key=lambda x: x['item_name'])

        return jsonify({
            'success': True,
            'unit_detail_id': unit_detail_id,
            'room_name': unit_detail.room_name or 'Ruangan Tanpa Nama',
            'assets': grouped_assets,
            'total_count': len(assets),
            'total_items': len(grouped_assets)
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
