from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db, login_manager
from app.models import User, ActivityLog
from app.forms import LoginForm

bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            # Check if user is inactive
            if not user.is_active:
                flash('Akun Anda dinonaktifkan. Mohon hubungi admin.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user)
            ActivityLog.log_activity(user, 'LOGIN', 'users', user.id, ip_address=request.remote_addr)

            # Redirect based on user role
            if user.is_admin():
                return redirect(url_for('dashboard.admin_index'))
            elif user.is_warehouse_staff():
                return redirect(url_for('dashboard.warehouse_index'))
            elif user.is_field_staff():
                return redirect(url_for('dashboard.field_index'))
            elif user.is_unit_staff():
                return redirect(url_for('dashboard.unit_index'))
        else:
            flash('Email atau password salah.', 'danger')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    ActivityLog.log_activity(current_user, 'LOGOUT', 'users', current_user.id, ip_address=request.remote_addr)
    logout_user()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profile')
@login_required
def profile():
    """Display user profile"""
    return render_template('auth/profile.html', user=current_user)


@bp.route('/profile/upload', methods=['POST'])
@login_required
def upload_profile_image():
    """Handle profile image upload"""
    if 'profile_image' not in request.files:
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(url_for('auth.profile'))

    file = request.files['profile_image']

    if file.filename == '':
        flash('Tidak ada file yang dipilih.', 'danger')
        return redirect(url_for('auth.profile'))

    if not allowed_file(file.filename):
        flash('Format file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, atau WEBP.', 'danger')
        return redirect(url_for('auth.profile'))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        flash('Ukuran file terlalu besar. Maksimal 5MB.', 'danger')
        return redirect(url_for('auth.profile'))

    try:
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)

        # Delete old profile image if exists
        if current_user.profile_image:
            old_path = os.path.join(current_app.root_path, 'static', current_user.profile_image)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass  # Ignore errors when deleting old file

        # Save new file
        filename = secure_filename(f"{current_user.id}_{file.filename}")
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Update user profile
        relative_path = f"uploads/profiles/{filename}"
        current_user.profile_image = relative_path
        db.session.commit()

        ActivityLog.log_activity(current_user, 'UPDATE', 'users', current_user.id,
                                details='Update profile image', ip_address=request.remote_addr)

        flash('Foto profil berhasil diperbarui.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Gagal mengupload foto profil. Silakan coba lagi.', 'danger')
        print(f"Error uploading profile image: {str(e)}")

    return redirect(url_for('auth.profile'))


@bp.route('/profile/remove-image', methods=['POST'])
@login_required
def remove_profile_image():
    """Remove profile image"""
    try:
        # Delete old profile image if exists
        if current_user.profile_image:
            old_path = os.path.join(current_app.root_path, 'static', current_user.profile_image)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass  # Ignore errors when deleting old file

        current_user.profile_image = None
        db.session.commit()

        ActivityLog.log_activity(current_user, 'UPDATE', 'users', current_user.id,
                                details='Remove profile image', ip_address=request.remote_addr)

        flash('Foto profil berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Gagal menghapus foto profil.', 'danger')
        print(f"Error removing profile image: {str(e)}")

    return redirect(url_for('auth.profile'))
