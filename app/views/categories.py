from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Category, Item
from app.forms.item_forms import CategoryForm
from app.utils.decorators import role_required
from sqlalchemy import or_

bp = Blueprint('categories', __name__, url_prefix='/admin/categories')


@bp.route('/')
@login_required
@role_required('admin', 'warehouse_staff')
def index():
    """List all categories"""
    search = request.args.get('search', '')

    query = Category.query

    # Search
    if search:
        query = query.filter(Category.name.ilike(f'%{search}%'))

    categories = query.order_by(Category.name).all()

    # Get item count for each category
    category_item_counts = {}
    for category in categories:
        category_item_counts[category.id] = Item.query.filter_by(category_id=category.id).count()

    return render_template('admin/categories/index.html',
                         categories=categories,
                         category_item_counts=category_item_counts,
                         search=search)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse_staff')
def create():
    """Create new category"""
    form = CategoryForm()

    if form.validate_on_submit():
        try:
            # Check if category name already exists
            if Category.query.filter_by(name=form.name.data).first():
                flash('Kategori dengan nama ini sudah ada!', 'danger')
                return render_template('admin/categories/create.html', form=form)

            # Check if category code already exists
            if Category.query.filter_by(code=form.code.data.upper()).first():
                flash('Kategori dengan kode ini sudah ada!', 'danger')
                return render_template('admin/categories/create.html', form=form)

            # Create category
            category = Category(
                name=form.name.data,
                code=form.code.data.upper(),  # Convert to uppercase
                description=form.description.data,
                require_serial_number=form.require_serial_number.data == 'True'
            )
            category.save()

            flash(f'Kategori {category.name} ({category.code}) berhasil dibuat!', 'success')
            return redirect(url_for('categories.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # Get all categories for validation
    categories = Category.query.all()
    categories_data = [{'id': c.id, 'name': c.name, 'code': c.code} for c in categories]

    return render_template('admin/categories/create.html', form=form, categories=categories_data)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warehouse_staff')
def edit(id):
    """Edit category"""
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)

    # Set require_serial_number value manually for RadioField
    if not form.is_submitted():
        form.require_serial_number.data = 'True' if category.require_serial_number else 'False'

    if form.validate_on_submit():
        try:
            # Check if category name already exists (excluding current)
            existing_category = Category.query.filter(
                Category.name == form.name.data,
                Category.id != id
            ).first()

            if existing_category:
                flash('Kategori dengan nama ini sudah ada!', 'danger')
                return render_template('admin/categories/edit.html', category=category, form=form)

            # Check if category code already exists (excluding current)
            existing_code = Category.query.filter(
                Category.code == form.code.data.upper(),
                Category.id != id
            ).first()

            if existing_code:
                flash('Kategori dengan kode ini sudah ada!', 'danger')
                return render_template('admin/categories/edit.html', category=category, form=form)

            # Update category
            category.name = form.name.data
            category.code = form.code.data.upper()  # Convert to uppercase
            category.description = form.description.data
            category.require_serial_number = form.require_serial_number.data == 'True'
            category.save()

            flash(f'Kategori {category.name} ({category.code}) berhasil diupdate!', 'success')
            return redirect(url_for('categories.index'))

        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # Get all categories for validation
    categories = Category.query.all()
    categories_data = [{'id': c.id, 'name': c.name, 'code': c.code} for c in categories]

    return render_template('admin/categories/edit.html', category=category, form=form, categories=categories_data)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    """Delete category"""
    category = Category.query.get_or_404(id)

    # Check if category has items
    item_count = Item.query.filter_by(category_id=id).count()
    if item_count > 0:
        flash(f'Tidak bisa menghapus kategori yang masih memiliki {item_count} barang!', 'warning')
        return redirect(url_for('categories.index'))

    try:
        category.delete()
        flash(f'Kategori {category.name} berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('categories.index'))
