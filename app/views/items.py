from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Item, ItemDetail, Category
from app.forms import CategoryForm, ItemForm, ItemDetailForm
from app.utils.decorators import role_required
from app.utils.helpers import generate_barcode
import os

bp = Blueprint('items', __name__, url_prefix='/items')


@bp.route('/categories')
@login_required
def categories():
    """List all categories"""
    categories = Category.query.all()
    return render_template('items/categories.html', categories=categories)


@bp.route('/category/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_category():
    """Create new category"""
    form = CategoryForm()

    if form.validate_on_submit():
        try:
            category = Category(
                name=form.name.data,
                description=form.description.data
            )
            category.save()

            flash('Kategori berhasil dibuat!', 'success')
            return redirect(url_for('items.categories'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('items/create_category.html', form=form)


@bp.route('/')
@login_required
def index():
    """List all items with category filter"""
    category_id = request.args.get('category_id', '', type=int)
    query = Item.query

    if category_id:
        query = query.filter_by(category_id=category_id)

    items = query.all()
    categories = Category.query.all()

    return render_template('items/index.html', items=items, categories=categories, current_filter=category_id)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create():
    """Create new item"""
    form = ItemForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        try:
            item = Item(
                name=form.name.data,
                item_code=form.item_code.data,
                unit=form.unit.data,
                category_id=form.category_id.data
            )
            item.save()

            flash('Barang berhasil dibuat!', 'success')
            return redirect(url_for('items.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('items/create.html', form=form)


@bp.route('/<int:id>/details')
@login_required
def details(id):
    """Show item details and list of item details (serial numbers)"""
    item = Item.query.get_or_404(id)
    item_details = ItemDetail.query.filter_by(item_id=id).all()

    return render_template('items/details.html', item=item, item_details=item_details)


@bp.route('/detail/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def create_detail():
    """Create new item detail (add serial number)"""
    form = ItemDetailForm()

    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    if current_user.is_warehouse_staff():
        form.warehouse_id.choices = [(current_user.warehouse.id, current_user.warehouse.name)]
    else:
        from app.models import Warehouse
        form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    from app.models import Supplier
    form.supplier_id.choices = [(0, 'Tanpa Supplier')] + [(s.id, s.name) for s in Supplier.query.all()]

    if form.validate_on_submit():
        try:
            item_detail = ItemDetail(
                item_id=form.item_id.data,
                serial_number=form.serial_number.data,
                warehouse_id=form.warehouse_id.data,
                status=form.status.data,
                specification_notes=form.specification_notes.data
            )

            if form.supplier_id.data != 0:
                item_detail.supplier_id = form.supplier_id.data

            item_detail.save()

            # Update stock
            from app.models import Stock
            stock = Stock.query.filter_by(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data
            ).first()

            if not stock:
                stock = Stock(
                    item_id=form.item_id.data,
                    warehouse_id=form.warehouse_id.data,
                    quantity=0
                )
                stock.save()

            stock.add_stock(1)

            flash('Item detail berhasil dibuat!', 'success')
            return redirect(url_for('items.details', id=form.item_id.data))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('items/create_detail.html', form=form)


@bp.route('/barcode/<serial_number>')
@login_required
def barcode(serial_number):
    """Generate barcode for item"""
    return generate_barcode(serial_number)


@bp.route('/search')
@login_required
def search():
    """Search items"""
    query = request.args.get('q', '')

    items = Item.query.filter(
        db.or_(
            Item.name.ilike(f'%{query}%'),
            Item.item_code.ilike(f'%{query}%')
        )
    ).all()

    return render_template('items/search.html', items=items, query=query)
