from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Distribution
from app.utils.decorators import role_required
from werkzeug.utils import secure_filename
import os
from datetime import datetime

bp = Blueprint('field_tasks', __name__, url_prefix='/field-tasks')


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@login_required
@role_required('field_staff')
def index():
    """List all tasks for current field staff"""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    task_type_filter = request.args.get('task_type', '')
    verification_filter = request.args.get('verification', '')

    # Build query
    query = Distribution.query.filter_by(field_staff_id=current_user.id)

    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if task_type_filter:
        query = query.filter_by(task_type=task_type_filter)
    if verification_filter:
        query = query.filter_by(verification_status=verification_filter)

    # Get tasks ordered by created_at
    tasks = query.order_by(Distribution.created_at.desc()).all()

    # Calculate statistics
    total_tasks = len(tasks)
    pending_tasks = len([t for t in tasks if t.verification_status == 'pending'])
    submitted_tasks = len([t for t in tasks if t.verification_status == 'submitted'])
    verified_tasks = len([t for t in tasks if t.verification_status == 'verified'])
    rejected_tasks = len([t for t in tasks if t.verification_status == 'rejected'])

    installation_tasks = len([t for t in tasks if t.task_type == 'installation'])
    delivery_tasks = len([t for t in tasks if t.task_type == 'delivery'])

    return render_template('field_tasks/index.html',
                         tasks=tasks,
                         total_tasks=total_tasks,
                         pending_tasks=pending_tasks,
                         submitted_tasks=submitted_tasks,
                         verified_tasks=verified_tasks,
                         rejected_tasks=rejected_tasks,
                         installation_tasks=installation_tasks,
                         delivery_tasks=delivery_tasks,
                         status_filter=status_filter,
                         task_type_filter=task_type_filter,
                         verification_filter=verification_filter)


@bp.route('/<int:id>/detail')
@login_required
@role_required('field_staff')
def detail(id):
    """View task detail"""
    task = Distribution.query.get_or_404(id)

    # Ensure task belongs to current field staff
    if task.field_staff_id != current_user.id:
        flash('Anda tidak memiliki akses ke tugas ini.', 'danger')
        return redirect(url_for('field_tasks.index'))

    return render_template('field_tasks/detail.html', task=task)


@bp.route('/<int:id>/verify', methods=['GET', 'POST'])
@login_required
@role_required('field_staff')
def submit_verification(id):
    """Submit verification with photo and notes"""
    task = Distribution.query.get_or_404(id)

    # Ensure task belongs to current field staff
    if task.field_staff_id != current_user.id:
        flash('Anda tidak memiliki akses ke tugas ini.', 'danger')
        return redirect(url_for('field_tasks.index'))

    # Check if task can be verified
    if task.verification_status == 'verified':
        flash('Tugas ini sudah diverifikasi.', 'info')
        return redirect(url_for('field_tasks.detail', id=id))

    if request.method == 'POST':
        # Handle file upload
        photo_file = request.files.get('verification_photo')
        notes = request.form.get('notes', '')

        photo_path = None
        if photo_file and photo_file.filename:
            if allowed_file(photo_file.filename):
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'verifications')
                os.makedirs(upload_dir, exist_ok=True)

                # Generate unique filename
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{photo_file.filename}")
                photo_path = os.path.join('uploads', 'verifications', filename).replace('\\', '/')
                full_path = os.path.join(current_app.root_path, 'static', photo_path)
                photo_file.save(full_path)
            else:
                flash('Format file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP.', 'danger')
                return redirect(url_for('field_tasks.submit_verification', id=id))

        # Submit verification
        success, message = task.submit_verification(photo_path, notes)
        if success:
            flash(message, 'success')
            return redirect(url_for('field_tasks.detail', id=id))
        else:
            flash(message, 'danger')

    return render_template('field_tasks/submit_verification.html', task=task)


@bp.route('/<int:id>/start', methods=['POST'])
@login_required
@role_required('field_staff')
def start_task(id):
    """Mark task as in progress (in transit for delivery)"""
    task = Distribution.query.get_or_404(id)

    # Ensure task belongs to current field staff
    if task.field_staff_id != current_user.id:
        flash('Anda tidak memiliki akses ke tugas ini.', 'danger')
        return redirect(url_for('field_tasks.index'))

    # Update status based on task type
    if task.task_type == 'delivery':
        task.mark_in_transit()
        flash('Status tugas diperbarui menjadi "Sedang Dikirim".', 'success')
    else:
        flash('Status tugas diperbarui.', 'success')

    return redirect(url_for('field_tasks.detail', id=id))


@bp.route('/map')
@login_required
@role_required('field_staff')
def map_view():
    """View map with assigned task locations"""
    tasks = Distribution.query.filter_by(field_staff_id=current_user.id).all()

    # Group tasks by status for the map
    pending_tasks = [t for t in tasks if t.verification_status == 'pending']
    in_progress_tasks = [t for t in tasks if t.verification_status == 'submitted']
    completed_tasks = [t for t in tasks if t.verification_status == 'verified']

    # Convert tasks to serializable format for the map
    tasks_data = []
    for task in tasks:
        coords = task.get_coordinates()
        task_dict = {
            'id': task.id,
            'task_type': task.task_type,
            'verification_status': task.verification_status,
            'status': task.status,
            'address': task.address,
            'note': task.note,
            'geom': {
                'coordinates': [coords['longitude'], coords['latitude']]
            } if coords else None,
            'item_detail': {
                'id': task.item_detail.id,
                'serial_number': task.item_detail.serial_number,
                'item': {
                    'id': task.item_detail.item.id,
                    'name': task.item_detail.item.name
                } if task.item_detail.item else None
            } if task.item_detail else None,
            'unit': {
                'id': task.unit.id,
                'name': task.unit.name
            } if task.unit else None,
            'unit_detail': {
                'id': task.unit_detail.id,
                'room_name': task.unit_detail.room_name
            } if task.unit_detail else None
        }
        tasks_data.append(task_dict)

    return render_template('field_tasks/map.html',
                         tasks=tasks_data,
                         pending_tasks=pending_tasks,
                         in_progress_tasks=in_progress_tasks,
                         completed_tasks=completed_tasks)
