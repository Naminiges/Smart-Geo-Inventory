from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import User, ActivityLog
from app.forms import LoginForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


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

    # Debug: Print session and cookie info
    if request.method == 'GET':
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
        print(f"DEBUG: Generated CSRF token: {csrf_token[:20]}...")
        print(f"DEBUG: Session: {session}")
        print(f"DEBUG: Session cookie in request: {request.cookies.get('smart_geo_session', 'Not found')}")
    elif request.method == 'POST':
        print(f"DEBUG: POST request - Session: {session}")
        print(f"DEBUG: POST request - Session cookie: {request.cookies.get('smart_geo_session', 'Not found')}")

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

    # If form validation failed, print errors
    if request.method == 'POST' and not form.validate_on_submit():
        print(f"DEBUG: Form validation failed. Errors: {form.errors}")
        if 'csrf_token' in form.errors:
            print(f"DEBUG: CSRF token errors: {form.errors['csrf_token']}")

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


@bp.route('/test-csrf')
def test_csrf():
    """Test CSRF token generation and session configuration"""
    form = LoginForm()
    return render_template('test_csrf.html', form=form, config=current_app.config)


