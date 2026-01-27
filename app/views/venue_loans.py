from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import VenueLoan, Unit, UnitDetail, User, Distribution, ItemDetail
from app.utils.decorators import role_required

bp = Blueprint('venue_loans', __name__, url_prefix='/venue-loans')


# ==================== UNIT STAFF VIEWS ====================

@bp.route('/unit')
@login_required
@role_required('unit_staff')
def unit_index():
    """List all venue loans for unit staff"""
    # Get units assigned to this user
    user_units = current_user.get_assigned_units()

    if not user_units:
        flash('Anda belum ditugaskan ke unit manapun.', 'warning')
        return redirect(url_for('dashboard.index'))

    # Get unit IDs
    unit_ids = [unit.id for unit in user_units]

    # Get venue loans for these units (as borrower)
    venue_loans = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids)
    ).order_by(VenueLoan.created_at.desc()).all()

    # Get currently active events (within time range, regardless of status)
    from app.utils.datetime_helper import get_wib_now
    now = get_wib_now()
    print(f"DEBUG: Current time (WIB): {now}")
    print(f"DEBUG: Total venue_loans: {len(venue_loans)}")

    currently_active_loans = []
    for loan in venue_loans:
        print(f"DEBUG: Loan {loan.id} - {loan.event_name} - status: {loan.status}")
        print(f"DEBUG:   start: {loan.start_datetime}, end: {loan.end_datetime}")
        print(f"DEBUG:   start <= now: {loan.start_datetime <= now}, now <= end: {now <= loan.end_datetime}")
        if loan.start_datetime <= now <= loan.end_datetime and loan.status in ['approved', 'active']:
            currently_active_loans.append(loan)
            print(f"DEBUG:   -> ACTIVE!")

    print(f"DEBUG: Current active loans count: {len(currently_active_loans)}")

    # Get statistics
    total_count = VenueLoan.query.filter(VenueLoan.borrower_unit_id.in_(unit_ids)).count()
    pending_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'pending'
    ).count()

    # Active count includes both 'active' status and 'approved' within time range
    active_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'active'
    ).count()
    # Add approved loans that are within time range
    for loan in venue_loans:
        if loan.status == 'approved' and loan.start_datetime <= now <= loan.end_datetime:
            active_count += 1

    approved_count = VenueLoan.query.filter(
        VenueLoan.borrower_unit_id.in_(unit_ids),
        VenueLoan.status == 'approved'
    ).count()

    return render_template('venue_loans/unit/index.html',
                         venue_loans=venue_loans,
                         currently_active_loans=currently_active_loans,
                         user_units=user_units,
                         stats={
                             'total': total_count,
                             'pending': pending_count,
                             'active': active_count,
                             'approved': approved_count
                         })


@bp.route('/unit/request', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def unit_request():
    """Create new venue loan request (Unit staff)"""
    # Get units assigned to this user
    user_units = current_user.get_assigned_units()

    if not user_units:
        flash('Anda belum ditugaskan ke unit manapun.', 'warning')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        try:
            # Get form data
            unit_detail_id = request.form.get('unit_detail_id', type=int)
            borrower_unit_id = request.form.get('borrower_unit_id', type=int)
            event_name = request.form.get('event_name', '')
            start_datetime_str = request.form.get('start_datetime', '')
            end_datetime_str = request.form.get('end_datetime', '')
            notes = request.form.get('notes', '')

            # Validate required fields
            if not all([unit_detail_id, borrower_unit_id, event_name, start_datetime_str, end_datetime_str]):
                flash('Semua field wajib diisi!', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            # Verify user has access to borrower unit
            if not any(unit.id == borrower_unit_id for unit in user_units):
                flash('Anda tidak memiliki akses ke unit ini.', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            # Parse datetime
            try:
                start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
                end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Format tanggal/waktu tidak valid!', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            # Validate datetime
            if end_datetime <= start_datetime:
                flash('Waktu selesai harus setelah waktu mulai!', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            if start_datetime < datetime.utcnow():
                flash('Waktu mulai tidak boleh di masa lalu!', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            # Check if venue is already booked for the requested time
            conflicting_loans = VenueLoan.query.filter(
                VenueLoan.unit_detail_id == unit_detail_id,
                VenueLoan.status.in_(['approved', 'active']),
                VenueLoan.start_datetime < end_datetime,
                VenueLoan.end_datetime > start_datetime
            ).first()

            if conflicting_loans:
                flash('Ruangan sudah dipesan untuk waktu yang diminta!', 'danger')
                return render_template('venue_loans/unit/request.html',
                                     user_units=user_units,
                                     all_units=Unit.query.all(),
                                     all_unit_details=UnitDetail.query.all())

            # Create venue loan
            venue_loan = VenueLoan(
                unit_detail_id=unit_detail_id,
                borrower_unit_id=borrower_unit_id,
                borrower_user_id=current_user.id,
                event_name=event_name,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                notes=notes,
                status='pending'
            )
            venue_loan.save()

            flash('Permohonan peminjaman tempat berhasil dibuat!', 'success')
            return redirect(url_for('asset_loans.unit_index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show form
    return render_template('venue_loans/unit/request.html',
                         user_units=user_units,
                         all_units=Unit.query.all(),
                         all_unit_details=UnitDetail.query.all())


@bp.route('/unit/<int:id>')
@login_required
@role_required('unit_staff')
def unit_detail(id):
    """View venue loan detail (Unit staff)"""
    venue_loan = VenueLoan.query.get_or_404(id)

    # Check permission - only borrower can view
    user_units = current_user.get_assigned_units()
    if not any(unit.id == venue_loan.borrower_unit_id for unit in user_units):
        flash('Anda tidak memiliki izin untuk melihat detail ini.', 'danger')
        return redirect(url_for('venue_loans.unit_index'))

    return render_template('venue_loans/unit/detail.html', venue_loan=venue_loan)


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
    """Get unit details for a specific unit (AJAX)"""
    unit_details = UnitDetail.query.filter_by(unit_id=unit_id).order_by(
        UnitDetail.room_name
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
            'unit_name': ud.unit.name if ud.unit else ''
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
