from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Procurement, Supplier, Item, User, Warehouse
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('api_procurement', __name__)


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
            new_item = Item(
                name=data['item_name'],
                item_code=f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                category='uncategorized'
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
    """Step 3: Admin approves and selects supplier"""
    procurement = Procurement.query.get_or_404(id)
    data = request.get_json()

    if procurement.status != 'pending':
        return jsonify({
            'success': False,
            'message': 'Hanya permohonan dengan status pending yang bisa disetujui'
        }), 400

    if 'supplier_id' not in data:
        return jsonify({
            'success': False,
            'message': 'supplier_id is required'
        }), 400

    try:
        success, message = procurement.approve(
            user_id=current_user.id,
            supplier_id=data['supplier_id']
        )

        if success:
            if 'unit_price' in data:
                procurement.unit_price = data['unit_price']
            if 'notes' in data:
                procurement.notes = data['notes']
            procurement.save()

            return jsonify({
                'success': True,
                'message': f'{message}. Supplier telah dipilih',
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
