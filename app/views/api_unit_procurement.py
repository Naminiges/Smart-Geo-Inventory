from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (
    UnitProcurement, UnitProcurementItem, Unit,
    Supplier, Item, User, Warehouse
)
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('api_unit_procurement', __name__)


# ==================== UNIT STAFF API ====================

@bp.route('/unit-procurements', methods=['GET'])
@login_required
@role_required('unit_staff')
def get_unit_procurements():
    """Get all procurement requests for the unit"""
    status_filter = request.args.get('status', '')

    # Get user's unit
    user_unit = current_user.units.first()
    if not user_unit:
        return jsonify({
            'success': False,
            'message': 'Anda belum ditugaskan ke unit manapun'
        }), 400

    query = UnitProcurement.query.filter_by(unit_id=user_unit.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    procurements = query.order_by(UnitProcurement.created_at.desc()).all()

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in procurements]
    })


@bp.route('/unit-procurements/<int:id>', methods=['GET'])
@login_required
@role_required('unit_staff')
def get_unit_procurement(id):
    """Get single procurement request details"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Check if user belongs to this unit
    user_unit = current_user.units.first()
    if not user_unit or procurement.unit_id != user_unit.id:
        return jsonify({
            'success': False,
            'message': 'Anda tidak memiliki akses ke permohonan ini'
        }), 403

    # Update status from linked procurement if exists
    if procurement.procurement:
        procurement.update_status_from_procurement()

    return jsonify({
        'success': True,
        'data': procurement.to_dict()
    })


@bp.route('/unit-procurements/request', methods=['POST'])
@login_required
@role_required('unit_staff')
def create_request():
    """Create procurement request (same as warehouse procurement request)"""
    data = request.get_json()

    # Get user's unit
    user_unit = current_user.units.first()
    if not user_unit:
        return jsonify({
            'success': False,
            'message': 'Anda belum ditugaskan ke unit manapun'
        }), 400

    # Validate required fields
    if 'request_notes' not in data:
        return jsonify({
            'success': False,
            'message': 'Field request_notes is required'
        }), 400

    if 'items' not in data or not data['items']:
        return jsonify({
            'success': False,
            'message': 'Minimal harus ada satu barang yang diminta'
        }), 400

    try:
        # Create unit procurement
        unit_procurement = UnitProcurement(
            unit_id=user_unit.id,
            request_notes=data['request_notes'],
            status='pending_verification',
            requested_by=current_user.id,
            request_date=datetime.now()
        )
        unit_procurement.save()

        # Process items
        for item_data in data['items']:
            # Handle item selection
            if item_data.get('item_id') and item_data['item_id'] != -1:
                item_id = item_data['item_id']
            elif item_data.get('item_name'):
                # Create new item
                new_item = Item(
                    name=item_data['item_name'],
                    item_code=f"NEW-{datetime.now().strftime('%Y%m%d%H%M%S')}-{item_data.get('item_name', 'unknown')}",
                    category_id=item_data.get('item_category_id'),
                    unit=item_data.get('item_unit', 'pcs')
                )
                new_item.save()
                item_id = new_item.id
            else:
                # Rollback and return error
                unit_procurement.delete()
                return jsonify({
                    'success': False,
                    'message': 'Either item_id or item_name must be provided for each item'
                }), 400

            # Create unit procurement item
            procurement_item = UnitProcurementItem(
                unit_procurement_id=unit_procurement.id,
                item_id=item_id,
                quantity=item_data['quantity']
            )
            procurement_item.save()

        return jsonify({
            'success': True,
            'message': 'Permohonan pengadaan berhasil dibuat',
            'data': unit_procurement.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@bp.route('/unit-procurements/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('unit_staff')
def cancel_request(id):
    """Cancel procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Check if user belongs to this unit
    user_unit = current_user.units.first()
    if not user_unit or procurement.unit_id != user_unit.id:
        return jsonify({
            'success': False,
            'message': 'Anda tidak memiliki akses ke permohonan ini'
        }), 403

    success, message = procurement.cancel(current_user.id)

    if success:
        return jsonify({
            'success': True,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@bp.route('/unit-procurements/<int:id>/progress', methods=['GET'])
@login_required
@role_required('unit_staff')
def get_progress(id):
    """Get procurement progress tracking"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Check if user belongs to this unit
    user_unit = current_user.units.first()
    if not user_unit or procurement.unit_id != user_unit.id:
        return jsonify({
            'success': False,
            'message': 'Anda tidak memiliki akses ke permohonan ini'
        }), 403

    # Update status from linked procurement if exists
    if procurement.procurement:
        procurement.update_status_from_procurement()

    # Build progress data
    progress = {
        'status': procurement.status,
        'status_display': procurement.get_status_display(),
        'created_at': procurement.created_at.isoformat(),
        'request_notes': procurement.request_notes,
        'has_procurement': procurement.has_procurement,
        'procurement_id': procurement.procurement_id,
        'procurement_status': procurement.procurement.status if procurement.procurement else None,
        'steps': [
            {
                'step': 'Permohonan Dibuat',
                'completed': True,
                'date': procurement.created_at.isoformat(),
                'description': 'Permohonan telah diajukan oleh unit'
            },
            {
                'step': 'Verifikasi Admin',
                'completed': procurement.is_verified,
                'date': procurement.verification_date.isoformat() if procurement.verification_date else None,
                'description': 'Admin memverifikasi permohonan'
            },
            {
                'step': 'Persetujuan & Pembuatan Pengadaan',
                'completed': procurement.status in ['approved', 'in_procurement', 'received', 'completed'],
                'date': procurement.approval_date.isoformat() if procurement.approval_date else None,
                'description': f'Pengadaan #{procurement.procurement_id} dibuat' if procurement.procurement_id else 'Menunggu persetujuan'
            },
            {
                'step': 'Dalam Proses Pengadaan',
                'completed': procurement.status in ['in_procurement', 'received', 'completed'],
                'description': 'Barang sedang dalam proses pengadaan oleh warehouse'
            },
            {
                'step': 'Barang Diterima',
                'completed': procurement.status in ['received', 'completed'],
                'date': procurement.unit_receipt_date.isoformat() if procurement.unit_receipt_date else None,
                'description': 'Barang telah diterima dan siap digunakan'
            },
            {
                'step': 'Selesai',
                'completed': procurement.status == 'completed',
                'date': procurement.procurement.completion_date.isoformat() if procurement.procurement and procurement.procurement.completion_date else None,
                'description': 'Permohonan telah selesai'
            }
        ]
    }

    return jsonify({
        'success': True,
        'data': progress
    })


# ==================== ADMIN API ====================

@bp.route('/admin/unit-procurements', methods=['GET'])
@login_required
@role_required('admin')
def admin_get_unit_procurements():
    """Get all unit procurement requests for admin"""
    status_filter = request.args.get('status', '')
    unit_filter = request.args.get('unit', '')

    query = UnitProcurement.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if unit_filter:
        query = query.filter_by(unit_id=unit_filter)

    procurements = query.order_by(UnitProcurement.created_at.desc()).all()

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in procurements]
    })


@bp.route('/admin/unit-procurements/<int:id>', methods=['GET'])
@login_required
@role_required('admin')
def admin_get_unit_procurement(id):
    """Get single procurement request details for admin"""
    procurement = UnitProcurement.query.get_or_404(id)

    # Update status from linked procurement if exists
    if procurement.procurement:
        procurement.update_status_from_procurement()

    return jsonify({
        'success': True,
        'data': procurement.to_dict()
    })


@bp.route('/admin/unit-procurements/<int:id>/verify', methods=['POST'])
@login_required
@role_required('admin')
def verify_request(id):
    """Admin verifies unit procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status != 'pending_verification':
        return jsonify({
            'success': False,
            'message': 'Hanya permohonan dengan status pending_verification yang bisa diverifikasi'
        }), 400

    data = request.get_json()

    success, message = procurement.verify(
        user_id=current_user.id,
        notes=data.get('verification_notes')
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


@bp.route('/admin/unit-procurements/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_request(id):
    """Admin approves verified request and creates warehouse procurement"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status != 'verified':
        return jsonify({
            'success': False,
            'message': 'Hanya permohonan yang sudah diverifikasi yang bisa disetujui'
        }), 400

    data = request.get_json()

    success, message = procurement.approve(user_id=current_user.id)

    if success:
        # Add admin notes
        if data.get('admin_notes'):
            procurement.admin_notes = data['admin_notes']

        # Set supplier to the linked warehouse procurement
        if data.get('supplier_id') and procurement.procurement:
            procurement.procurement.supplier_id = data['supplier_id']
            procurement.procurement.save()

        procurement.save()

        return jsonify({
            'success': True,
            'message': f'{message} Supplier telah dipilih.',
            'data': procurement.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@bp.route('/admin/unit-procurements/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_request(id):
    """Admin rejects unit procurement request"""
    procurement = UnitProcurement.query.get_or_404(id)

    if procurement.status in ['completed', 'in_procurement']:
        return jsonify({
            'success': False,
            'message': 'Tidak bisa menolak permohonan yang sedang diproses atau sudah selesai'
        }), 400

    data = request.get_json()

    if not data.get('rejection_reason'):
        return jsonify({
            'success': False,
            'message': 'Alasan penolakan harus diisi'
        }), 400

    success, message = procurement.reject(
        user_id=current_user.id,
        reason=data['rejection_reason']
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


@bp.route('/admin/unit-procurements/stats', methods=['GET'])
@login_required
@role_required('admin')
def get_stats():
    """Get unit procurement statistics"""
    total = UnitProcurement.query.count()
    pending_verification = UnitProcurement.query.filter_by(status='pending_verification').count()
    verified = UnitProcurement.query.filter_by(status='verified').count()
    approved = UnitProcurement.query.filter_by(status='approved').count()
    in_procurement = UnitProcurement.query.filter_by(status='in_procurement').count()
    received = UnitProcurement.query.filter_by(status='received').count()
    completed = UnitProcurement.query.filter_by(status='completed').count()
    rejected = UnitProcurement.query.filter_by(status='rejected').count()

    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'pending_verification': pending_verification,
            'verified': verified,
            'approved': approved,
            'in_procurement': in_procurement,
            'received': received,
            'completed': completed,
            'rejected': rejected
        }
    })
