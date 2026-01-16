from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Warehouse, UserWarehouse
from app.forms.user_forms import UserForm, UserWarehouseAssignmentForm
from app.utils.decorators import role_required
from sqlalchemy import or_

bp = Blueprint('users', __name__, url_prefix='/admin/users')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """List all users"""
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    warehouse_filter = request.args.get('warehouse', '')

    query = User.query

    # Search
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )

    # Role filter
    if role_filter:
        query = query.filter_by(role=role_filter)

    # Warehouse filter
    if warehouse_filter:
        query = query.join(UserWarehouse).filter_by(warehouse_id=warehouse_filter)

    users = query.order_by(User.created_at.desc()).all()
    warehouses = Warehouse.query.all()

    # Get warehouse assignments for each user
    user_warehouses = {}
    for user in users:
        user_warehouses[user.id] = [uw.warehouse for uw in user.user_warehouses.all()]

    return render_template('admin/users/index.html',
                         users=users,
                         warehouses=warehouses,
                         user_warehouses=user_warehouses,
                         search=search,
                         role_filter=role_filter,
                         warehouse_filter=warehouse_filter)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create new user"""
    form = UserForm()

    if form.validate_on_submit():
        try:
            # Check if email already exists
            if User.query.filter_by(email=form.email.data).first():
                flash('Email sudah terdaftar!', 'danger')
                return render_template('admin/users/create.html', form=form)

            # Create user
            user = User(
                name=form.name.data,
                email=form.email.data,
                role=form.role.data
            )

            # Set password if provided
            if form.password.data:
                user.set_password(form.password.data)
            else:
                # Set default password
                user.set_password('123456')

            user.save()
            flash(f'User {user.name} berhasil dibuat! Password default: 123456', 'success')
            return redirect(url_for('users.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/users/create.html', form=form)


@bp.route('/<int:id>')
@login_required
@role_required('admin')
def detail(id):
    """View user detail"""
    user = User.query.get_or_404(id)

    # Get warehouse assignments
    warehouse_assignments = user.user_warehouses.all()
    warehouses = [uw.warehouse for uw in warehouse_assignments]

    return render_template('admin/users/detail.html',
                         user=user,
                         warehouse_assignments=warehouse_assignments,
                         warehouses=warehouses)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit user"""
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        try:
            # Check if email exists (excluding current user)
            existing_user = User.query.filter(
                User.email == form.email.data,
                User.id != id
            ).first()

            if existing_user:
                flash('Email sudah digunakan user lain!', 'danger')
                return render_template('admin/users/edit.html', user=user, form=form)

            # Update user
            user.name = form.name.data
            user.email = form.email.data
            user.role = form.role.data

            # Update password if provided
            if form.password.data:
                user.set_password(form.password.data)

            user.save()
            flash(f'User {user.name} berhasil diupdate!', 'success')
            return redirect(url_for('users.detail', id=id))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('admin/users/edit.html', user=user, form=form)


@bp.route('/<int:id>/assign-warehouses', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def assign_warehouses(id):
    """Assign warehouse to user (single warehouse)"""
    user = User.query.get_or_404(id)
    form = UserWarehouseAssignmentForm()

    # Populate warehouse choices
    warehouses = Warehouse.query.all()
    form.warehouse_id.choices = [(0, '-- Pilih Warehouse --')] + [(w.id, w.name) for w in warehouses]

    # Get current assignment
    current_assignment = user.user_warehouses.first()
    current_warehouse_id = current_assignment.warehouse_id if current_assignment else None

    if form.validate_on_submit():
        try:
            # Get selected warehouse
            selected_warehouse_id = form.warehouse_id.data

            # Remove old assignments
            UserWarehouse.query.filter_by(user_id=id).delete()

            # Add new assignment if warehouse is selected
            if selected_warehouse_id and selected_warehouse_id != 0:
                user_warehouse = UserWarehouse(
                    user_id=id,
                    warehouse_id=selected_warehouse_id
                )
                db.session.add(user_warehouse)

            db.session.commit()
            flash(f'Warehouse assignment untuk {user.name} berhasil diupdate!', 'success')
            return redirect(url_for('users.detail', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # Pre-select current assignment
    form.warehouse_id.data = current_warehouse_id or 0

    return render_template('admin/users/assign_warehouses.html',
                         user=user,
                         form=form,
                         warehouses=warehouses)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete user"""
    user = User.query.get_or_404(id)

    # Prevent deleting self
    if user.id == current_user.id:
        flash('Tidak bisa menghapus user yang sedang login!', 'danger')
        return redirect(url_for('users.index'))

    try:
        # Delete warehouse assignments
        UserWarehouse.query.filter_by(user_id=id).delete()

        # Delete user
        user.delete()
        flash(f'User {user.name} berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('users.index'))
