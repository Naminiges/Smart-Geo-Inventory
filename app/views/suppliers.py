from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Supplier
from app.forms import SupplierForm
from app.utils.decorators import role_required

bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@bp.route('/')
@login_required
def index():
    """List all suppliers"""
    suppliers = Supplier.query.all()
    return render_template('suppliers/index.html', suppliers=suppliers)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create new supplier"""
    form = SupplierForm()

    if form.validate_on_submit():
        try:
            supplier = Supplier(
                name=form.name.data,
                contact_person=form.contact_person.data,
                phone=form.phone.data,
                email=form.email.data,
                address=form.address.data
            )
            supplier.save()

            flash('Supplier berhasil dibuat!', 'success')
            return redirect(url_for('suppliers.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('suppliers/create.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit(id):
    """Edit supplier"""
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)

    if form.validate_on_submit():
        try:
            supplier.name = form.name.data
            supplier.contact_person = form.contact_person.data
            supplier.phone = form.phone.data
            supplier.email = form.email.data
            supplier.address = form.address.data
            supplier.save()

            flash('Supplier berhasil diperbarui!', 'success')
            return redirect(url_for('suppliers.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('suppliers/edit.html', form=form, supplier=supplier)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete supplier"""
    supplier = Supplier.query.get_or_404(id)

    try:
        supplier.delete()
        flash('Supplier berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('suppliers.index'))
