from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Procurement, Item, User, Warehouse, Category
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('api_procurement', __name__)


def generate_item_code(category_id):
    """Generate item code based on category code"""
    category = Category.query.get(category_id)
    if not category or not category.code:
        # Fallback if category has no code
        return f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    prefix = category.code.upper()

    # Find the last item code with this prefix
    last_item = Item.query.filter(Item.item_code.like(f'{prefix}-%')).order_by(Item.item_code.desc()).first()

    if last_item and last_item.item_code:
        # Extract the number from the last item code (e.g., JAR-001 -> 001)
        try:
            last_number = int(last_item.item_code.split('-')[1])
            new_number = last_number + 1
        except (IndexError, ValueError):
            new_number = 1
    else:
        new_number = 1

    # Format: PREFIX-001 (3 digits)
    return f"{prefix}-{new_number:03d}"


@bp.route('/procurements', methods=['GET'])
@login_required
@role_required('admin', 'warehouse_staff')
def get_procurements():
    """Get all procurements with optional filtering"""
    status_filter = request.args.get('status', '')

    query = Procurement.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    procurements = query.order_by(Procurement.created_at.desc()).all()

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in procurements]
    })


@bp.route('/procurements/<int:id>', methods=['GET'])
@login_required
@role_required('admin', 'warehouse_staff')
def get_procurement(id):
    """Get single procurement details"""
    procurement = Procurement.query.get_or_404(id)

    return jsonify({
        'success': True,
        'data': procurement.to_dict()
    })


@bp.route('/procurements/request', methods=['POST'])
@login_required
@role_required('warehouse_staff')
def create_request():
    """Step 1-2: Create procurement request"""
    data = request.get_json()

    # Validate required fields
    required_fields = ['quantity', 'request_notes']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Field {field} is required'
            }), 400

    try:
        # Handle item selection
        if data.get('item_id') and data['item_id'] != 0:
            item_id = data['item_id']
        elif data.get('item_name'):
            # Create new item
            category_id = data.get('item_category_id')
            if not category_id:
                return jsonify({
                    'success': False,
                    'message': 'Kategori barang harus dipilih untuk barang baru'
                }), 400

            # Generate item code based on category
            item_code = generate_item_code(category_id)

            new_item = Item(
                name=data['item_name'],
                item_code=item_code,
                category_id=category_id,
                unit=data.get('item_unit', 'pcs')
            )
            new_item.save()
            item_id = new_item.id
        else:
            return jsonify({
                'success': False,
                'message': 'Either item_id or item_name must be provided'
            }), 400

        # Create procurement request
        procurement = Procurement(
            item_id=item_id,
            quantity=data['quantity'],
            request_notes=data['request_notes'],
            status='pending',
            requested_by=current_user.id,
            request_date=datetime.now()
        )
        procurement.save()

        return jsonify({
            'success': True,
            'message': 'Permohonan pengadaan berhasil dibuat',
            'data': procurement.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_request(id):
    """Step 3: Admin approves procurement request"""
    procurement = Procurement.query.get_or_404(id)
    data = request.get_json()

    if procurement.status != 'pending':
        return jsonify({
            'success': False,
            'message': 'Hanya permohonan dengan status pending yang bisa disetujui'
        }), 400

    try:
        success, message = procurement.approve(
            user_id=current_user.id
        )

        if success:
            if 'unit_price' in data:
                procurement.unit_price = data['unit_price']
            if 'notes' in data:
                procurement.notes = data['notes']
            procurement.save()

            return jsonify({
                'success': True,
                'message': f'{message}',
                'data': procurement.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_request(id):
    """Reject procurement request"""
    procurement = Procurement.query.get_or_404(id)
    data = request.get_json()

    try:
        success, message = procurement.reject(
            current_user.id,
            data.get('rejection_reason')
        )

        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': procurement.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/<int:id>/receive', methods=['POST'])
@login_required
@role_required('warehouse_staff')
def receive_goods(id):
    """Step 4-5: Record goods receipt"""
    procurement = Procurement.query.get_or_404(id)
    data = request.get_json()

    if procurement.status != 'approved':
        return jsonify({
            'success': False,
            'message': 'Hanya pengadaan yang sudah disetujui yang bisa menerima barang'
        }), 400

    required_fields = ['receipt_number', 'actual_quantity', 'unit_type']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Field {field} is required'
            }), 400

    try:
        success, message = procurement.receive_goods(
            user_id=current_user.id,
            receipt_number=data['receipt_number'],
            actual_quantity=data['actual_quantity'],
            barcode=data.get('barcode'),
            unit_type=data['unit_type'],
            other_unit=data.get('other_unit') if data['unit_type'] == 'lainnya' else None
        )

        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': procurement.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/<int:id>/complete', methods=['POST'])
@login_required
@role_required('warehouse_staff')
def complete_procurement(id):
    """Step 6: Complete procurement and add to stock"""
    procurement = Procurement.query.get_or_404(id)
    data = request.get_json()

    if procurement.status != 'received':
        return jsonify({
            'success': False,
            'message': 'Hanya pengadaan yang sudah diterima barangnya yang bisa diselesaikan'
        }), 400

    if 'warehouse_id' not in data:
        return jsonify({
            'success': False,
            'message': 'warehouse_id is required'
        }), 400

    try:
        success, message = procurement.complete(
            user_id=current_user.id,
            warehouse_id=data['warehouse_id']
        )

        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': procurement.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/<int:id>/delete', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_procurement(id):
    """Delete procurement request"""
    procurement = Procurement.query.get_or_404(id)

    if procurement.status not in ['pending', 'rejected']:
        return jsonify({
            'success': False,
            'message': 'Hanya permohonan dengan status pending atau rejected yang bisa dihapus'
        }), 400

    try:
        procurement.delete()
        return jsonify({
            'success': True,
            'message': 'Pengadaan berhasil dihapus'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/procurements/stats', methods=['GET'])
@login_required
@role_required('admin', 'warehouse_staff')
def get_statistics():
    """Get procurement statistics"""
    try:
        total = Procurement.query.count()
        pending = Procurement.query.filter_by(status='pending').count()
        approved = Procurement.query.filter_by(status='approved').count()
        received = Procurement.query.filter_by(status='received').count()
        completed = Procurement.query.filter_by(status='completed').count()
        rejected = Procurement.query.filter_by(status='rejected').count()

        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'pending': pending,
                'approved': approved,
                'received': received,
                'completed': completed,
                'rejected': rejected
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
