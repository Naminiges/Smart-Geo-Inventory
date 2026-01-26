from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Item, ItemDetail, Category
from app.forms import CategoryForm, ItemForm, ItemDetailForm
from app.utils.decorators import role_required
from app.utils.helpers import generate_barcode, get_user_warehouse_id
import os

bp = Blueprint('items', __name__, url_prefix='/items')


@bp.route('/categories')
@login_required
@role_required('admin', 'warehouse_staff')
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
@role_required('admin', 'warehouse_staff')
def index():
    """List all items with category filter and search"""
    category_id = request.args.get('category_id', '', type=int)
    search = request.args.get('search', '')

    query = Item.query

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(
            db.or_(
                Item.name.ilike(f'%{search}%'),
                Item.item_code.ilike(f'%{search}%')
            )
        )

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
@role_required('admin', 'warehouse_staff')
def details(id):
    """Show item details and list of item details (serial numbers)"""
    from app.models import Warehouse, Unit, Distribution, ReturnItem, VenueLoan

    item = Item.query.get_or_404(id)

    # Get filter parameters
    location_filter = request.args.get('location', '')
    search_filter = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')

    # Build query for item details - NO warehouse filter, show all item_details
    query = ItemDetail.query.filter_by(item_id=id)
    item_details = query.all()

    # Filter by status
    if status_filter:
        if status_filter == 'used_in_unit':
            # Gabungkan status 'used' dan 'in_unit'
            item_details = [d for d in item_details if d.status in ['used', 'in_unit']]
        else:
            item_details = [d for d in item_details if d.status == status_filter]

    # Filter by location
    if location_filter:
        if ':' in location_filter:
            filter_type, filter_id = location_filter.split(':', 1)
            filter_id = int(filter_id)

            if filter_type == 'warehouse':
                # Filter by warehouse from item_details table
                item_details = [d for d in item_details if d.warehouse_id == filter_id]
            elif filter_type == 'unit':
                # Filter by unit from distributions table
                distributed_detail_ids = db.session.query(Distribution.item_detail_id).filter_by(unit_id=filter_id).all()
                distributed_detail_ids = [d[0] for d in distributed_detail_ids]
                item_details = [d for d in item_details if d.id in distributed_detail_ids]

    # Filter by serial number search
    if search_filter:
        item_details = [d for d in item_details if search_filter.lower() in d.serial_number.lower()]

    # Build combined location list for dropdown - show all warehouses and units
    locations = []
    for warehouse in Warehouse.query.all():
        locations.append({
            'value': f'warehouse:{warehouse.id}',
            'name': f'Warehouse: {warehouse.name}',
            'type': 'warehouse'
        })
    for unit in Unit.query.all():
        locations.append({
            'value': f'unit:{unit.id}',
            'name': f'Unit: {unit.name}',
            'type': 'unit'
        })

    # Get ReturnItem data for items with 'returned' status
    return_items_map = {}
    returned_detail_ids = [d.id for d in item_details if d.status == 'returned']
    if returned_detail_ids:
        return_items = ReturnItem.query.filter(
            ReturnItem.item_detail_id.in_(returned_detail_ids),
            ReturnItem.status == 'returned'
        ).all()
        return_items_map = {ri.item_detail_id: ri for ri in return_items}

    # Get VenueLoan data for items with 'loaned' status (via specification_notes)
    venue_loans_map = {}
    loaned_detail_ids = [d.id for d in item_details if d.status == 'loaned']
    if loaned_detail_ids:
        # Get active venue loans
        active_venue_loans = VenueLoan.query.filter(
            VenueLoan.status.in_(['approved', 'active'])
        ).all()

        # Build map of unit_detail_id to venue_loan
        for vl in active_venue_loans:
            venue_loans_map[vl.unit_detail_id] = vl

    return render_template('items/details.html', item=item, item_details=item_details,
                          locations=locations, location_filter=location_filter,
                          status_filter=status_filter, search_filter=search_filter,
                          return_items_map=return_items_map,
                          venue_loans_map=venue_loans_map)


@bp.route('/detail/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def create_detail():
    """Create new item detail (add serial number)"""
    form = ItemDetailForm()

    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    warehouse_id = get_user_warehouse_id(current_user)
    if warehouse_id:
        # Warehouse staff only sees their warehouse
        from app.models import Warehouse
        warehouse = Warehouse.query.get(warehouse_id)
        form.warehouse_id.choices = [(warehouse.id, warehouse.name)] if warehouse else []
    else:
        # Admin sees all warehouses
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
@role_required('admin', 'warehouse_staff')
def barcode(serial_number):
    """Generate barcode for item"""
    return generate_barcode(serial_number)


@bp.route('/search')
@login_required
@role_required('admin', 'warehouse_staff')
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
