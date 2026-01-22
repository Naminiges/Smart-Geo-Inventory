from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AssetRequest, AssetRequestItem, Item, Unit, UnitDetail, User
from app.forms import AssetRequestForm, AssetVerificationForm
from app.utils.decorators import role_required
from datetime import datetime

bp = Blueprint('asset_requests', __name__, url_prefix='/asset-requests')


@bp.route('/')
@login_required
@role_required('unit_staff', 'admin', 'warehouse_staff')
def index():
    """List all asset requests"""
    from app.models import UserUnit

    status_filter = request.args.get('status', '')

    # Filter based on role
    if current_user.is_unit_staff():
        # Unit staff can only see requests for their units
        user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
        if not user_units:
            flash('Anda belum terassign ke unit manapun.', 'danger')
            return redirect(url_for('dashboard.index'))

        # Get unit IDs from user_units
        unit_ids = [uu.unit_id for uu in user_units]
        query = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids))
    elif current_user.is_warehouse_staff():
        # Warehouse staff can see requests that need processing or are being processed
        # They can see: verified (ready to distribute), distributing (in process), completed (done)
        query = AssetRequest.query.filter(AssetRequest.status.in_(['verified', 'distributing', 'completed']))
    else:  # admin
        query = AssetRequest.query

    # Apply additional status filter if specified
    if status_filter:
        # For warehouse staff, only allow filtering through their visible statuses
        if current_user.is_warehouse_staff():
            allowed_statuses = ['verified', 'distributing', 'completed']
            if status_filter in allowed_statuses:
                query = query.filter_by(status=status_filter)
            # If invalid filter, don't apply it (show all visible)
        else:
            query = query.filter_by(status=status_filter)

    asset_requests = query.order_by(AssetRequest.created_at.desc()).all()

    # Convert to list to avoid len() error
    asset_requests_list = list(asset_requests)

    # Get statistics based on role
    if current_user.is_unit_staff():
        total_requests = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids)).count()
        pending_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'pending').count()
        verified_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'verified').count()
        distributing_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'distributing').count()
        completed_count = AssetRequest.query.filter(AssetRequest.unit_id.in_(unit_ids), AssetRequest.status == 'completed').count()
    elif current_user.is_warehouse_staff():
        total_requests = AssetRequest.query.filter(AssetRequest.status.in_(['verified', 'distributing', 'completed'])).count()
        pending_count = 0  # Warehouse staff doesn't see pending
        verified_count = AssetRequest.query.filter_by(status='verified').count()
        distributing_count = AssetRequest.query.filter_by(status='distributing').count()
        completed_count = AssetRequest.query.filter_by(status='completed').count()
    else:  # admin
        total_requests = AssetRequest.query.count()
        pending_count = AssetRequest.query.filter_by(status='pending').count()
        verified_count = AssetRequest.query.filter_by(status='verified').count()
        distributing_count = AssetRequest.query.filter_by(status='distributing').count()
        completed_count = AssetRequest.query.filter_by(status='completed').count()

    return render_template('asset_requests/index.html',
                         asset_requests=asset_requests_list,
                         stats={
                             'total': total_requests,
                             'pending': pending_count,
                             'verified': verified_count,
                             'distributing': distributing_count,
                             'completed': completed_count,
                             'rejected': 0  # Will calculate if needed
                         },
                         current_filter=status_filter)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def create():
    """Create new asset request"""
    from app.models import UserUnit

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('asset_requests.index'))

    # For now, just use the first assigned unit
    # TODO: Allow user to select which unit to request for
    user_unit = user_units[0]

    form = AssetRequestForm()

    if request.method == 'POST':
        try:
            # Get items data from form
            items_data = request.form.getlist('items')
            request_notes = form.request_notes.data

            if not items_data or len(items_data) == 0:
                flash('Minimal harus ada satu aset yang diminta!', 'danger')
                return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

            # Validate and process items
            import json
            valid_items = []
            for item_json in items_data:
                item_data = json.loads(item_json)

                # Validate
                if not item_data.get('item_id') or item_data.get('item_id') == 0:
                    flash('Harap pilih aset dari daftar!', 'danger')
                    return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

                quantity = item_data.get('quantity')
                if not quantity or quantity <= 0:
                    flash('Harap isi jumlah aset dengan benar!', 'danger')
                    return render_template('asset_requests/create.html', form=form, unit=user_unit.unit)

                valid_items.append({
                    'item_id': item_data.get('item_id'),
                    'quantity': quantity,
                    'unit_detail_id': item_data.get('unit_detail_id'),
                    'room_notes': item_data.get('room_notes', '')
                })

            # Create asset request
            asset_request = AssetRequest(
                unit_id=user_unit.unit_id,
                requested_by=current_user.id,
                request_date=datetime.now(),
                request_notes=request_notes,
                status='pending'
            )
            asset_request.save()

            # Create asset request items
            for item_data in valid_items:
                asset_request_item = AssetRequestItem(
                    asset_request_id=asset_request.id,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity'],
                    unit_detail_id=item_data.get('unit_detail_id'),
                    room_notes=item_data.get('room_notes', '')
                )
                asset_request_item.save()

            item_count = len(valid_items)
            flash(f'Permohonan aset berhasil dibuat dengan {item_count} aset! Menunggu verifikasi admin.', 'success')

            return redirect(url_for('asset_requests.index'))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - prepare data
    items = Item.query.all()
    unit_details = UnitDetail.query.filter_by(unit_id=user_unit.unit_id).all()

    return render_template('asset_requests/create.html',
                         form=form,
                         items=items,
                         unit_details=unit_details,
                         unit=user_unit.unit)


@bp.route('/<int:id>')
@login_required
def detail(id):
    """Show asset request details"""
    asset_request = AssetRequest.query.get_or_404(id)

    # Check permission based on role
    if current_user.is_unit_staff():
        from app.models import UserUnit
        user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
        unit_ids = [uu.unit_id for uu in user_units]
        if asset_request.unit_id not in unit_ids:
            flash('Anda tidak memiliki izin untuk melihat permohonan ini.', 'danger')
            return redirect(url_for('asset_requests.index'))
    elif current_user.is_warehouse_staff():
        # Warehouse staff can see verified, distributing, and completed requests
        if asset_request.status not in ['verified', 'distributing', 'completed']:
            flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('asset_requests.index'))
    # Admin can see all requests

    return render_template('asset_requests/detail.html', asset_request=asset_request)


@bp.route('/<int:id>/verify', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def verify(id):
    """Verify asset request (admin only)"""
    from app.models import Warehouse, ItemDetail

    asset_request = AssetRequest.query.get_or_404(id)

    if asset_request.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa diverifikasi.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    # Get all warehouses
    warehouses = Warehouse.query.all()

    # Get stock information for each warehouse
    warehouse_stock_info = {}
    for warehouse in warehouses:
        warehouse_stock_info[warehouse.id] = {}
        for item in asset_request.items:
            # Get available item_details with status 'available'
            # Ini adalah source of truth untuk ketersediaan barang
            available_details = ItemDetail.query.filter_by(
                warehouse_id=warehouse.id,
                item_id=item.item_id,
                status='available'
            ).count()

            warehouse_stock_info[warehouse.id][item.item_id] = {
                'requested': item.quantity,
                'available': available_details,
                'is_sufficient': available_details >= item.quantity
            }

    form = AssetVerificationForm()

    # Set choices for form (both GET and POST)
    form.warehouse_id.choices = [('0', '-- Pilih Warehouse --')] + [(str(w.id), w.name) for w in warehouses]

    if request.method == 'POST':
        # DEBUG: Print all form data
        print(f"=== DEBUG FORM SUBMISSION ===")
        print(f"Request form keys: {list(request.form.keys())}")
        print(f"Request form data: {dict(request.form)}")
        print(f"warehouse_id value: {request.form.get('warehouse_id')}")
        print(f"warehouse_id type: {type(request.form.get('warehouse_id'))}")
        print(f"warehouse_id == '0': {request.form.get('warehouse_id') == '0'}")
        print(f"============================")

        # Manually validate CSRF token
        if not form.validate():
            # Form has errors (likely CSRF)
            print(f"Form validation errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
            return render_template('asset_requests/verify.html',
                                 asset_request=asset_request,
                                 form=form,
                                 warehouse_stock_info=warehouse_stock_info,
                                 warehouses=warehouses)

        try:
            # Get warehouse ID from form data
            warehouse_id_str = request.form.get('warehouse_id', '0')

            print(f"Extracted warehouse_id_str: '{warehouse_id_str}'")

            # Manually validate warehouse selection
            if not warehouse_id_str or warehouse_id_str == '0' or warehouse_id_str.strip() == '':
                print(f"Warehouse validation FAILED: warehouse_id_str='{warehouse_id_str}'")
                flash('Silakan pilih warehouse terlebih dahulu.', 'warning')
                return render_template('asset_requests/verify.html',
                                     asset_request=asset_request,
                                     form=form,
                                     warehouse_stock_info=warehouse_stock_info,
                                     warehouses=warehouses)

            selected_warehouse_id = int(warehouse_id_str)

            stock_warnings = []

            for item in asset_request.items:
                stock_info = warehouse_stock_info[selected_warehouse_id][item.item_id]
                if not stock_info['is_sufficient']:
                    stock_warnings.append(
                        f"{item.item.name}: tersedia {stock_info['available']}, diminta {stock_info['requested']}"
                    )

            # Verify the request
            success, message = asset_request.verify(
                user_id=current_user.id,
                notes=form.notes.data
            )

            if success:
                # Store selected warehouse in the request for later use
                # We'll use the notes field to store this info temporarily
                if not asset_request.notes:
                    asset_request.notes = f"warehouse_id:{selected_warehouse_id}"
                else:
                    asset_request.notes = f"{asset_request.notes}\nwarehouse_id:{selected_warehouse_id}"
                asset_request.save()

                if stock_warnings:
                    warning_msg = "Peringatan Stok: " + ", ".join(stock_warnings)
                    flash(f'{message} {warning_msg}', 'warning')
                else:
                    flash(f'{message} Permohonan siap diproses.', 'success')

                return redirect(url_for('asset_requests.detail', id=id))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('asset_requests/verify.html',
                         asset_request=asset_request,
                         form=form,
                         warehouse_stock_info=warehouse_stock_info,
                         warehouses=warehouses)


@bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject(id):
    """Reject asset request (admin only)"""
    asset_request = AssetRequest.query.get_or_404(id)

    if asset_request.status != 'pending':
        flash('Hanya permohonan dengan status pending yang bisa ditolak.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    rejection_reason = request.form.get('rejection_reason', '')

    try:
        success, message = asset_request.reject(
            user_id=current_user.id,
            reason=rejection_reason
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('asset_requests.detail', id=id))


@bp.route('/<int:id>/distribute', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def distribute(id):
    """Process verified asset request into distribution (warehouse/admin)"""
    from app.models import Distribution, ItemDetail, Warehouse

    asset_request = AssetRequest.query.get_or_404(id)

    # Check if request is verified
    if asset_request.status != 'verified':
        flash('Hanya permohonan yang sudah diverifikasi yang bisa diproses.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    # Extract warehouse_id from notes if available
    warehouse_id = None
    if asset_request.notes and 'warehouse_id:' in asset_request.notes:
        try:
            for line in asset_request.notes.split('\n'):
                if 'warehouse_id:' in line:
                    warehouse_id = int(line.split('warehouse_id:')[1].strip())
                    break
        except:
            pass

    if not warehouse_id:
        # Get first warehouse as default
        warehouse = Warehouse.query.first()
        if not warehouse:
            flash('Warehouse tidak tersedia.', 'danger')
            return redirect(url_for('asset_requests.detail', id=id))
        warehouse_id = warehouse.id

    if request.method == 'POST':
        try:
            from app.models.inventory import Stock
            # Create distributions for each item based on selected serial numbers
            distributions_created = []
            all_items_valid = True
            validation_errors = []

            for request_item in asset_request.items:
                # Get selected serial IDs from form
                selected_serials_key = f'selected_serials_{request_item.id}'
                selected_serials_str = request.form.get(selected_serials_key, '')

                if not selected_serials_str:
                    flash(f'Serial number belum dipilih untuk {request_item.item.name}. Silakan pilih serial number terlebih dahulu.', 'warning')
                    return redirect(url_for('asset_requests.distribute', id=id))

                # Parse selected serial IDs
                try:
                    selected_serial_ids = [int(sid.strip()) for sid in selected_serials_str.split(',') if sid.strip()]
                except ValueError:
                    flash(f'Format serial number tidak valid untuk {request_item.item.name}.', 'danger')
                    return redirect(url_for('asset_requests.distribute', id=id))

                # Validate quantity
                if len(selected_serial_ids) != request_item.quantity:
                    flash(f'Jumlah serial number yang dipilih untuk {request_item.item.name} tidak sesuai. '
                          f'Dipilih: {len(selected_serial_ids)}, Diminta: {request_item.quantity}', 'warning')
                    return redirect(url_for('asset_requests.distribute', id=id))

                # Get the selected item_details
                selected_item_details = ItemDetail.query.filter(
                    ItemDetail.id.in_(selected_serial_ids),
                    ItemDetail.warehouse_id == warehouse_id,
                    ItemDetail.item_id == request_item.item_id,
                    ItemDetail.status == 'available'
                ).all()

                # Validate all selected items are valid and available
                if len(selected_item_details) != len(selected_serial_ids):
                    found_ids = [item.id for item in selected_item_details]
                    missing_ids = set(selected_serial_ids) - set(found_ids)
                    flash(f'Beberapa serial number yang dipilih tidak valid atau tidak tersedia untuk {request_item.item.name}. '
                          f'Mohon refresh halaman dan pilih kembali.', 'danger')
                    return redirect(url_for('asset_requests.distribute', id=id))

                # Create distribution for each selected item_detail
                for item_detail in selected_item_details:
                    # Determine task type based on category
                    category_name = item_detail.item.category.name.lower() if item_detail.item and item_detail.item.category else ''
                    task_type = 'installation' if 'jaringan' in category_name or 'network' in category_name else 'delivery'

                    distribution = Distribution(
                        item_detail_id=item_detail.id,
                        warehouse_id=warehouse_id,
                        field_staff_id=current_user.id,  # Set to current user (warehouse staff)
                        unit_id=asset_request.unit_id,
                        unit_detail_id=request_item.unit_detail_id,
                        address=asset_request.unit.address if asset_request.unit else 'Unknown',
                        task_type=task_type,
                        asset_request_id=asset_request.id,
                        asset_request_item_id=request_item.id,
                        status='installing' if task_type == 'installation' else 'in_transit'
                    )
                    distribution.save()
                    distributions_created.append(distribution)

                # Update item_detail status
                for item_detail in selected_item_details:
                    item_detail.status = 'processing'
                    item_detail.save()

                # Update asset request item status
                request_item.status = 'distributing'
                request_item.save()

            # Update asset request status
            from datetime import datetime
            asset_request.status = 'distributing'
            asset_request.distribution_id = distributions_created[0].id if distributions_created else None
            asset_request.distributed_at = datetime.utcnow()
            asset_request.distributed_by = current_user.id
            asset_request.save()

            flash(f'Berhasil memproses {len(distributions_created)} distribusi. Barang sedang dipersiapkan untuk dikirim ke unit.', 'success')
            return redirect(url_for('asset_requests.detail', id=id))
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show summary
    return render_template('asset_requests/distribute.html', asset_request=asset_request, warehouse_id=warehouse_id)


@bp.route('/<int:id>/confirm-receipt', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def confirm_receipt(id):
    """Show confirmation page with photo upload for receiving items"""
    from app.models import Distribution
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    from PIL import Image

    def compress_image(image_bytes, max_size_kb=500, quality=85):
        """
        Compress image to reduce file size while maintaining quality

        Args:
            image_bytes: Original image bytes
            max_size_kb: Maximum target size in KB (default: 500KB)
            quality: Initial JPEG quality (1-100, default: 85)

        Returns:
            Compressed image bytes
        """
        img = Image.open(BytesIO(image_bytes))

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        # Calculate new dimensions if image is too large
        max_dimension = 1920  # Maximum width or height
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Start with initial quality
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_bytes = output.getvalue()

        # If still too large, reduce quality progressively
        min_quality = 50
        max_iterations = 10
        iteration = 0
        target_size = max_size_kb * 1024

        while len(compressed_bytes) > target_size and quality > min_quality and iteration < max_iterations:
            quality -= 5
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_bytes = output.getvalue()
            iteration += 1

        return compressed_bytes

    asset_request = AssetRequest.query.get_or_404(id)

    # Check permission
    from app.models import UserUnit
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    unit_ids = [uu.unit_id for uu in user_units]
    if asset_request.unit_id not in unit_ids:
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('asset_requests.detail', id=id))

    if asset_request.status not in ['verified', 'distributing']:
        flash('Hanya permohonan yang sedang didistribusikan yang bisa dikonfirmasi.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    # Get distributions for this asset request
    distributions = Distribution.query.filter_by(asset_request_id=id).all()

    if request.method == 'POST':
        try:
            # Get uploaded photo
            photo_file = request.files.get('proof_photo')

            if not photo_file:
                flash('Harap upload foto sebagai bukti penerimaan.', 'warning')
                return redirect(url_for('asset_requests.confirm_receipt', id=id))

            # Validate file type
            allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
            filename = photo_file.filename.lower()
            if not any(filename.endswith('.' + ext) for ext in allowed_extensions):
                flash('Format file tidak didukung. Gunakan JPG, PNG, GIF, atau WebP.', 'danger')
                return redirect(url_for('asset_requests.confirm_receipt', id=id))

            # Read file as bytes
            original_bytes = photo_file.read()

            if len(original_bytes) > 10 * 1024 * 1024:  # 10MB limit
                flash('Ukuran file terlalu besar. Maksimal 10MB.', 'danger')
                return redirect(url_for('asset_requests.confirm_receipt', id=id))

            # Compress image
            try:
                compressed_photo = compress_image(original_bytes, max_size_kb=500)
                original_size_kb = len(original_bytes) / 1024
                compressed_size_kb = len(compressed_photo) / 1024
                compression_ratio = (1 - compressed_size_kb / original_size_kb) * 100

                import logging
                logging.info(f'Image compressed: {original_size_kb:.2f}KB -> {compressed_size_kb:.2f}KB ({compression_ratio:.1f}% reduction)')
            except Exception as e:
                import logging
                logging.error(f'Image compression failed: {str(e)}')
                # Use original if compression fails
                compressed_photo = original_bytes

            # Get distribution_id from form
            distribution_id = request.form.get('distribution_id', type=int)
            if not distribution_id:
                distribution_id = asset_request.distribution_id

            # Update all distributions with the photo
            for dist in distributions:
                dist.verification_photo = compressed_photo
                dist.verification_status = 'submitted'
                dist.verification_notes = f'Bukti penerimaan dari {current_user.name}'
                dist.save()

            # Mark asset request as completed
            success, message = asset_request.mark_completed(
                distribution_id=distribution_id,
                user_id=current_user.id
            )

            if success:
                flash(f'{message} (Foto: {compressed_size_kb:.1f}KB)', 'success')
            else:
                flash(message, 'danger')

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

        return redirect(url_for('asset_requests.detail', id=id))

    # GET request - show confirmation form
    return render_template('asset_requests/confirm_receipt.html',
                         asset_request=asset_request,
                         distributions=distributions)


@bp.route('/<int:id>/proof-photo')
@login_required
def proof_photo(id):
    """Display proof photo for asset request"""
    from app.models import Distribution
    from flask import send_file
    from io import BytesIO

    asset_request = AssetRequest.query.get_or_404(id)

    # Get the first distribution with verification photo
    distribution = Distribution.query.filter_by(
        asset_request_id=id
    ).filter(Distribution.verification_photo != None).first()

    if not distribution or not distribution.verification_photo:
        # Return placeholder image
        # Create a simple placeholder SVG
        placeholder_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect width="400" height="300" fill="#f3f4f6"/>
    <text x="200" y="140" font-family="Arial, sans-serif" font-size="16" fill="#9ca3af" text-anchor="middle">
        <tspan x="200" dy="0">Foto tidak tersedia</tspan>
        <tspan x="200" dy="25" font-size="14">No proof photo uploaded</tspan>
    </text>
    <rect x="150" y="160" width="100" height="100" fill="none" stroke="#d1d5db" stroke-width="2" rx="8"/>
    <text x="200" y="220" font-family="Arial, sans-serif" font-size="40" fill="#d1d5db" text-anchor="middle">📷</text>
</svg>'''
        return send_file(BytesIO(placeholder_svg.encode('utf-8')),
                         mimetype='image/svg+xml',
                         as_attachment=False)

    # Return the photo from database
    return send_file(BytesIO(distribution.verification_photo),
                     mimetype='image/jpeg',
                     as_attachment=False)


@bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@role_required('unit_staff')
def complete(id):
    """Mark asset request as completed after receiving items"""
    asset_request = AssetRequest.query.get_or_404(id)

    # Check permission
    from app.models import UserUnit
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    unit_ids = [uu.unit_id for uu in user_units]
    if asset_request.unit_id not in unit_ids:
        flash('Anda tidak memiliki izin untuk menyelesaikan permohonan ini.', 'danger')
        return redirect(url_for('asset_requests.detail', id=id))

    if asset_request.status not in ['verified', 'distributing']:
        flash('Hanya permohonan yang sedang didistribusikan atau sudah diverifikasi yang bisa diselesaikan.', 'warning')
        return redirect(url_for('asset_requests.detail', id=id))

    distribution_id = request.form.get('distribution_id', type=int)

    if not distribution_id:
        # Use the distribution_id from asset_request if available
        distribution_id = asset_request.distribution_id

    if not distribution_id:
        flash('Distribution ID diperlukan.', 'danger')
        return redirect(url_for('asset_requests.detail', id=id))

    try:
        success, message = asset_request.mark_completed(
            distribution_id=distribution_id,
            user_id=current_user.id
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('asset_requests.detail', id=id))


@bp.route('/unit-assets')
@login_required
@role_required('unit_staff')
def unit_assets():
    """Show all assets in the unit staff's units"""
    from app.models import UserUnit
    from app.models.distribution import Distribution
    from app.models.master_data import ItemDetail
    from app.models.asset_request import AssetRequest
    from collections import defaultdict

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get all unit IDs
    unit_ids = [uu.unit_id for uu in user_units]

    # Get all distributions to these units that are installed/completed
    distributions = Distribution.query.filter(
        Distribution.unit_id.in_(unit_ids),
        Distribution.status.in_(['installed', 'completed'])
    ).all()

    # Group items by item_id
    items_dict = defaultdict(lambda: {
        'item': None,
        'details': [],
        'total_quantity': 0
    })

    # Collect all items from distributions
    for dist in distributions:
        if dist.item_detail and dist.item_detail.item:
            item_id = dist.item_detail.item_id
            items_dict[item_id]['item'] = dist.item_detail.item
            items_dict[item_id]['details'].append({
                'item_detail': dist.item_detail,
                'serial_number': dist.item_detail.serial_number,
                'distribution_date': dist.installed_at or dist.created_at,
                'location': f"{dist.unit.name} - {dist.unit_detail.room_name if dist.unit_detail else 'N/A'}",
                'status': dist.item_detail.status
            })
            items_dict[item_id]['total_quantity'] += 1

    # Also get items directly from ItemDetail with status 'in_unit' for this unit's distributions
    for unit_id in unit_ids:
        unit_distributions = Distribution.query.filter_by(unit_id=unit_id).all()

        if unit_distributions:
            item_details = ItemDetail.query.filter(
                ItemDetail.id.in_([d.item_detail_id for d in unit_distributions if d.item_detail_id]),
                ItemDetail.status == 'in_unit'
            ).all()

            for item_detail in item_details:
                if item_detail.item:
                    item_id = item_detail.item_id
                    items_dict[item_id]['item'] = item_detail.item

                    # Check if already added
                    existing_sn = [d['serial_number'] for d in items_dict[item_id]['details']]
                    if item_detail.serial_number not in existing_sn:
                        items_dict[item_id]['details'].append({
                            'item_detail': item_detail,
                            'serial_number': item_detail.serial_number,
                            'distribution_date': item_detail.updated_at,
                            'location': f"Unit {unit_id}",
                            'status': item_detail.status
                        })
                        items_dict[item_id]['total_quantity'] += 1

    # Convert to list for template
    unit_items = list(items_dict.values())

    # Get all units for display
    units = [uu.unit for uu in user_units]

    return render_template('asset_requests/unit_assets.html',
                         units=units,
                         unit_items=unit_items)


@bp.route('/api/available-items/<int:warehouse_id>/<int:item_id>')
@login_required
@role_required('warehouse_staff', 'admin')
def api_available_items(warehouse_id, item_id):
    """API endpoint to get available item details (serial numbers) for a specific item and warehouse"""
    from app.models import ItemDetail, Distribution
    from sqlalchemy import not_

    try:
        # Subquery to get item_detail_ids that have active distributions
        # We need to exclude items that are already in distributions table
        active_distribution_ids = db.session.query(Distribution.item_detail_id).filter(
            Distribution.item_detail_id.isnot(None)
        ).subquery()

        # Get items that are:
        # 1. In the specified warehouse
        # 2. Of the specified item type
        # 3. Have status 'available'
        # 4. NOT already in the distributions table (to avoid duplicates)
        available_items = ItemDetail.query.filter(
            ItemDetail.warehouse_id == warehouse_id,
            ItemDetail.item_id == item_id,
            ItemDetail.status == 'available',
            not_(ItemDetail.id.in_(active_distribution_ids))
        ).all()

        items_data = [{
            'id': item.id,
            'serial_number': item.serial_number,
            'serial_unit': item.serial_unit or '-'
        } for item in available_items]

        return jsonify({
            'success': True,
            'items': items_data,
            'total': len(items_data)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
