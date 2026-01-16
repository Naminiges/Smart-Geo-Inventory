from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
                return redirect(url_for('dashboard.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def warehouse_access_required(f):
    """Decorator to ensure warehouse staff can only access their assigned warehouse"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))

        if current_user.is_warehouse_staff() and not current_user.warehouse_id:
            flash('Anda belum ditugaskan ke gudang manapun.', 'danger')
            return redirect(url_for('dashboard.index'))

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    return role_required('admin')(f)


def warehouse_staff_required(f):
    """Decorator to require warehouse staff role"""
    return role_required('warehouse_staff')(f)


def field_staff_required(f):
    """Decorator to require field staff role"""
    return role_required('field_staff')(f)
