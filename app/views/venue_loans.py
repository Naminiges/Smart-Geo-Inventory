from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import VenueLoan, Unit, UnitDetail, User, Distribution, ItemDetail, Building
from app.utils.decorators import role_required

bp = Blueprint('venue_loans', __name__, url_prefix='/venue-loans')


# ==================== UNIT STAFF VIEWS ====================
# Venue loan features for unit staff have been disabled
# Only admin can manage venue loans now


# ==================== ADMIN VIEWS ====================

@bp.route('/admin/<int:id>')
@login_required
@role_required('admin')
def admin_detail(id):
    """View venue loan detail (Admin)"""
    venue_loan = VenueLoan.query.get_or_404(id)

    return render_template('venue_loans/admin/detail.html', venue_loan=venue_loan)


@bp.route('/admin/<int:id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def admin_approve(id):
    """Approve venue loan request"""
    venue_loan = VenueLoan.query.get_or_404(id)

    success, message = venue_loan.approve(current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('units.index'))


@bp.route('/admin/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def admin_reject(id):
    """Reject venue loan request"""
    venue_loan = VenueLoan.query.get_or_404(id)

    reason = request.form.get('reason', '')

    success, message = venue_loan.reject(current_user.id, reason)

    if success:
        flash(message, 'warning')
    else:
        flash(message, 'danger')

    return redirect(url_for('units.index'))


@bp.route('/admin/<int:id>/complete', methods=['POST'])
@login_required
@role_required('admin')
def admin_complete(id):
    """Complete venue loan - restore items to used status after time expires"""
    venue_loan = VenueLoan.query.get_or_404(id)

    success, message = venue_loan.complete(current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('units.index'))


# ==================== API ROUTES ====================

@bp.route('/api/unit-details/<int:unit_id>')
@login_required
def api_unit_details(unit_id):
    """Get all unit details (rooms) - shows all rooms regardless of unit selection"""
    # Get all unit details ordered by building and room name
    unit_details = UnitDetail.query.join(Building).order_by(
        Building.code, UnitDetail.room_name
    ).all()

    result = []
    for ud in unit_details:
        # Check if this room has items
        items_count = Distribution.query.filter_by(unit_detail_id=ud.id).count()

        result.append({
            'id': ud.id,
            'room_name': ud.room_name,
            'floor': ud.floor or '',
            'description': ud.description or '',
            'items_count': items_count,
            'building_code': ud.building.code if ud.building else ''
        })

    return jsonify(result)


@bp.route('/api/check-availability', methods=['POST'])
@login_required
def api_check_availability():
    """Check if venue is available for the requested time"""
    unit_detail_id = request.json.get('unit_detail_id')
    start_datetime_str = request.json.get('start_datetime')
    end_datetime_str = request.json.get('end_datetime')

    if not all([unit_detail_id, start_datetime_str, end_datetime_str]):
        return jsonify({'available': False, 'message': 'Parameter tidak lengkap'}), 400

    try:
        # Parse datetime
        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')

        # Validate datetime
        if start_datetime >= end_datetime:
            return jsonify({'available': False, 'message': 'Waktu selesai harus lebih besar dari waktu mulai'}), 400

        if start_datetime < datetime.now():
            return jsonify({'available': False, 'message': 'Waktu mulai tidak boleh di masa lalu'}), 400

        # Check for conflicting loans
        conflicting_loans = VenueLoan.query.filter(
            VenueLoan.unit_detail_id == unit_detail_id,
            VenueLoan.status.in_(['approved', 'active']),
            VenueLoan.start_datetime < end_datetime,
            VenueLoan.end_datetime > start_datetime
        ).first()

        if conflicting_loans:
            return jsonify({
                'available': False,
                'message': f'Ruangan sudah dipesan untuk acara: {conflicting_loans.event_name}'
            })

        return jsonify({'available': True, 'message': 'Ruangan tersedia'})

    except ValueError as e:
        return jsonify({'available': False, 'message': f'Format tanggal/waktu tidak valid: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'available': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500
