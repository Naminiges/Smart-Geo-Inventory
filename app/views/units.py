from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Unit, User, UserUnit, AssetRequest
from app.forms.unit_forms import UnitForm
from app.utils.decorators import role_required
from sqlalchemy import or_

bp = Blueprint('units', __name__, url_prefix='/admin/units')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """List venue loans for admin verification"""
    from app.models import VenueLoan

    status_filter = request.args.get('status', '')

    # Build query for venue loans
    query = VenueLoan.query

    # Status filter
    if status_filter:
        query = query.filter_by(status=status_filter)

    venue_loans = query.order_by(VenueLoan.created_at.desc()).all()

    # Get statistics
    total_count = VenueLoan.query.count()
    pending_count = VenueLoan.query.filter_by(status='pending').count()
    approved_count = VenueLoan.query.filter_by(status='approved').count()
    active_count = VenueLoan.query.filter_by(status='active').count()
    completed_count = VenueLoan.query.filter_by(status='completed').count()

    return render_template('admin/units/index.html',
                         venue_loans=venue_loans,
                         status_filter=status_filter,
                         stats={
                             'total': total_count,
                             'pending': pending_count,
                             'approved': approved_count,
                             'active': active_count,
                             'completed': completed_count
                         })


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create new unit"""
    form = UnitForm()

    if form.validate_on_submit():
        try:
            # Create unit
            unit = Unit(
                name=form.name.data,
                address=form.address.data,
                status=form.status.data
            )

            # Set coordinates if provided
            if form.latitude.data and form.longitude.data:
                unit.set_coordinates(form.latitude.data, form.longitude.data)

            unit.save()
            flash(f'Unit {unit.name} berhasil dibuat!', 'success')
            return redirect(url_for('units.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/units/create.html', form=form)


@bp.route('/<int:id>')
@login_required
@role_required('admin')
def detail(id):
    """View unit detail"""
    unit = Unit.query.get_or_404(id)

    # Get coordinates
    coordinates = unit.get_coordinates()

    # Get asset requests for this unit
    asset_requests = AssetRequest.query.filter_by(unit_id=id).order_by(AssetRequest.created_at.desc()).all()

    return render_template('admin/units/detail.html',
                         unit=unit,
                         coordinates=coordinates,
                         asset_requests=asset_requests)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit unit"""
    unit = Unit.query.get_or_404(id)
    form = UnitForm(obj=unit)

    # Pre-fill coordinates if available
    if request.method == 'GET':
        coordinates = unit.get_coordinates()
        if coordinates:
            form.latitude.data = coordinates['latitude']
            form.longitude.data = coordinates['longitude']

    if form.validate_on_submit():
        try:
            # Update unit
            unit.name = form.name.data
            unit.address = form.address.data
            unit.status = form.status.data

            # Update coordinates if provided
            if form.latitude.data and form.longitude.data:
                unit.set_coordinates(form.latitude.data, form.longitude.data)

            unit.save()
            flash(f'Unit {unit.name} berhasil diupdate!', 'success')
            return redirect(url_for('units.detail', id=id))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/units/edit.html', unit=unit, form=form)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete unit"""
    unit = Unit.query.get_or_404(id)

    try:
        # Check if unit has installations
        if unit.items_count > 0:
            flash(f'Tidak bisa menghapus unit yang masih memiliki {unit.items_count} item!', 'danger')
            return redirect(url_for('units.detail', id=id))

        # Delete unit
        unit.delete()
        flash(f'Unit {unit.name} berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('units.index'))


@bp.route('/<int:id>/assign-staffs', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def assign_staffs(id):
    """Assign unit staff to unit"""
    unit = Unit.query.get_or_404(id)

    if request.method == 'POST':
        try:
            # Get selected staff (only unit_staff role)
            selected_staff_ids = request.form.getlist('staff_ids')

            # Remove old assignments
            UserUnit.query.filter_by(unit_id=id).delete()

            # Add new assignments
            for staff_id in selected_staff_ids:
                if staff_id:  # Make sure staff_id is not empty
                    user_unit = UserUnit(
                        user_id=staff_id,
                        unit_id=id,
                        assigned_by=current_user.id
                    )
                    db.session.add(user_unit)

            db.session.commit()
            flash(f'Staff assignment untuk {unit.name} berhasil diupdate!', 'success')
            return redirect(url_for('units.detail', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show form
    # Get only users with unit_staff role
    staffs = User.query.filter_by(role='unit_staff').all()
    current_assignments = [uu.user_id for uu in unit.user_units]

    return render_template('admin/units/assign_staffs.html',
                         unit=unit,
                         staffs=staffs,
                         current_assignments=current_assignments)

