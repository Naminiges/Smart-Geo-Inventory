from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User, ActivityLog
from app.forms import LoginForm
from app.utils.helpers import get_user_warehouse_id
from app.utils.rate_limit_helpers import api_auth_limit

bp = Blueprint('api_auth', __name__)


@bp.route('/login', methods=['POST'])
@api_auth_limit  # Apply strict rate limiting for login (10 per minute)
def api_login():
    """API endpoint for login"""
    form = LoginForm()
    formdata = request.get_json()

    if not formdata:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    form.email.data = formdata.get('email')
    form.password.data = formdata.get('password')

    if form.validate():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            ActivityLog.log_activity(user, 'LOGIN_API', 'users', user.id, ip_address=request.remote_addr)

            return jsonify({
                'success': True,
                'message': 'Login berhasil',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Email atau password salah'}), 401
    else:
        return jsonify({'success': False, 'message': 'Data tidak valid', 'errors': form.errors}), 400


@bp.route('/logout', methods=['POST'])
def api_logout():
    """API endpoint for logout"""
    if current_user.is_authenticated:
        ActivityLog.log_activity(current_user, 'LOGOUT_API', 'users', current_user.id, ip_address=request.remote_addr)
        logout_user()

    return jsonify({'success': True, 'message': 'Logout berhasil'})


@bp.route('/me', methods=['GET'])
def api_me():
    """Get current user information"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'role': current_user.role,
            'warehouse_id': get_user_warehouse_id(current_user)
        }
    })
