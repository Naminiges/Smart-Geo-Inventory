from flask import Blueprint, request, jsonify
from flask_login import login_user
from app import db
from app.models import User, ActivityLog

bp = Blueprint('api_benchmark', __name__)


@bp.route('/login', methods=['POST'])
def benchmark_login():
    """
    Benchmark-only login endpoint without CSRF protection.
    This endpoint should ONLY be used for load testing and benchmarking.

    WARNING: This endpoint bypasses CSRF protection for automation purposes.
    Do NOT expose this in production without proper IP restrictions.
    """
    formdata = request.get_json()

    if not formdata:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    email = formdata.get('email')
    password = formdata.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        login_user(user)
        ActivityLog.log_activity(
            user,
            'LOGIN_BENCHMARK',
            'users',
            user.id,
            ip_address=request.remote_addr,
            details='Benchmark login via API'
        )

        return jsonify({
            'success': True,
            'message': 'Login berhasil (benchmark mode)',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Email atau password salah'}), 401
