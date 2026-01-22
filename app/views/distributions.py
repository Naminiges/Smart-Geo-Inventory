from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Distribution, UserUnit, Unit
from app.utils.decorators import role_required
from datetime import datetime
from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage

bp = Blueprint('distributions', __name__, url_prefix='/distributions')


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


@bp.route('/receive', methods=['GET'])
@login_required
@role_required('unit_staff')
def receive_index():
    """List all distribution batches that need to be received by unit staff"""
    from app.models import UserUnit, DistributionGroup

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Get all unit IDs
    unit_ids = [uu.unit_id for uu in user_units]

    # Get ONLY distribution groups (batches) that have distributions for user's units
    # We only want to show batches, not individual distributions
    distribution_groups = DistributionGroup.query.filter(
        DistributionGroup.is_draft == False,
        DistributionGroup.status == 'approved'
    ).join(Distribution).filter(
        Distribution.unit_id.in_(unit_ids),
        Distribution.verification_status == 'pending',
        Distribution.status.in_(['installing', 'in_transit'])
    ).distinct().order_by(DistributionGroup.verified_at.desc()).all()

    # Build batch data
    batch_list = []
    for group in distribution_groups:
        # Get all pending distributions for this batch and user's units
        batch_distributions = Distribution.query.filter(
            Distribution.distribution_group_id == group.id,
            Distribution.unit_id.in_(unit_ids),
            Distribution.verification_status == 'pending'
        ).all()

        if batch_distributions:  # Only add if there are pending distributions
            batch_list.append({
                'group': group,
                'distributions': batch_distributions,
                'warehouse': batch_distributions[0].warehouse if batch_distributions else None,
                'total_items': len(batch_distributions)
            })

    return render_template('distributions/receive_index.html',
                         batch_list=batch_list)


@bp.route('/receive/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def receive_detail(id):
    """Show distribution batch details and allow unit staff to confirm receipt"""
    from app.models import UserUnit

    # Get user's units
    user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not user_units:
        flash('Anda belum terassign ke unit manapun.', 'danger')
        return redirect(url_for('dashboard.index'))

    unit_ids = [uu.unit_id for uu in user_units]

    # Get the distribution
    distribution = Distribution.query.get_or_404(id)

    # Check if this distribution belongs to user's unit
    if distribution.unit_id not in unit_ids:
        flash('Anda tidak memiliki izin untuk mengakses distribusi ini.', 'danger')
        return redirect(url_for('distributions.receive_index'))

    # Check if already verified
    if distribution.verification_status != 'pending':
        flash('Distribusi ini sudah diverifikasi.', 'warning')
        return redirect(url_for('distributions.receive_index'))

    # Get distribution group (batch)
    if not distribution.distribution_group_id:
        flash('Distribusi ini bukan bagian dari batch.', 'danger')
        return redirect(url_for('distributions.receive_index'))

    # Get all distributions in this batch for user's units
    batch_distributions = Distribution.query.filter(
        Distribution.distribution_group_id == distribution.distribution_group_id,
        Distribution.unit_id.in_(unit_ids),
        Distribution.verification_status == 'pending'
    ).all()

    if not batch_distributions:
        flash('Tidak ada distribusi pending dalam batch ini.', 'warning')
        return redirect(url_for('distributions.receive_index'))

    distribution_group = distribution.distribution_group

    if request.method == 'POST':
        try:
            # Get uploaded photo
            photo_file = request.files.get('proof_photo')

            if not photo_file:
                flash('Harap upload foto sebagai bukti penerimaan.', 'warning')
                return redirect(url_for('distributions.receive_detail', id=id))

            # Validate file type
            allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
            filename = photo_file.filename.lower()
            if not any(filename.endswith('.' + ext) for ext in allowed_extensions):
                flash('Format file tidak didukung. Gunakan JPG, PNG, GIF, atau WebP.', 'danger')
                return redirect(url_for('distributions.receive_detail', id=id))

            # Read file as bytes
            original_bytes = photo_file.read()

            if len(original_bytes) > 10 * 1024 * 1024:  # 10MB limit
                flash('Ukuran file terlalu besar. Maksimal 10MB.', 'danger')
                return redirect(url_for('distributions.receive_detail', id=id))

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
                compressed_size_kb = len(original_bytes) / 1024

            # Update all distributions in this batch
            for dist in batch_distributions:
                dist.verification_status = 'submitted'
                dist.verification_notes = f'Bukti penerimaan batch {distribution_group.batch_code} dari {current_user.name}'
                dist.verified_by = current_user.id
                dist.verified_at = datetime.utcnow()
                dist.save()

                # Update item detail status
                if dist.item_detail:
                    dist.item_detail.status = 'used'
                    dist.item_detail.save()

                # Update distribution status
                dist.status = 'installed'
                dist.save()

            # Save photo to DistributionGroup (one photo for the entire batch)
            distribution_group.verification_photo = compressed_photo
            distribution_group.verification_received_by = current_user.id
            distribution_group.verification_received_at = datetime.utcnow()
            distribution_group.verification_notes = f'Bukti penerimaan batch {distribution_group.batch_code} dari {current_user.name}'
            distribution_group.save()

            item_count = len(batch_distributions)
            flash(f'Berhasil mengonfirmasi penerimaan batch {distribution_group.batch_code} dengan {item_count} barang. (Foto: {compressed_size_kb:.1f}KB)', 'success')

            return redirect(url_for('distributions.receive_index'))

        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    # GET request - show confirmation form
    return render_template('distributions/receive_detail.html',
                         distribution_group=distribution_group,
                         batch_distributions=batch_distributions,
                         warehouse=distribution.warehouse)


@bp.route('/proof-photo/<int:id>')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def proof_photo(id):
    """Display proof photo for distribution batch"""
    from flask import send_file
    from io import BytesIO

    distribution = Distribution.query.get_or_404(id)

    # Check permission
    if current_user.is_unit_staff():
        from app.models import UserUnit
        user_units = UserUnit.query.filter_by(user_id=current_user.id).all()
        unit_ids = [uu.unit_id for uu in user_units]
        if distribution.unit_id not in unit_ids:
            flash('Anda tidak memiliki izin untuk melihat foto ini.', 'danger')
            return redirect(url_for('distributions.receive_index'))

    # Try to get photo from DistributionGroup first (for direct distributions)
    if distribution.distribution_group and distribution.distribution_group.verification_photo:
        # Return the photo from distribution group
        return send_file(BytesIO(distribution.distribution_group.verification_photo),
                         mimetype='image/jpeg',
                         as_attachment=False)

    # Fallback to distribution's own photo (old data or individual distributions)
    if distribution.verification_photo:
        return send_file(BytesIO(distribution.verification_photo),
                         mimetype='image/jpeg',
                         as_attachment=False)

    # Return placeholder image
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
