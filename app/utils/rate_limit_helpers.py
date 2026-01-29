"""
Rate limiting decorators for API endpoints
Protects against API abuse and DDoS attacks
"""

from functools import wraps
from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app import limiter


# Custom rate limit decorators for different endpoint types

def api_standard_limit(f):
    """
    Standard rate limit for general API endpoints
    200 requests per day, 50 per hour
    """
    return limiter.limit("200 per day, 50 per hour")(f)


def api_strict_limit(f):
    """
    Stricter rate limit for expensive operations
    50 requests per day, 10 per hour
    Use for: bulk operations, exports, complex queries
    """
    return limiter.limit("50 per day, 10 per hour")(f)


def api_write_limit(f):
    """
    Rate limit for write operations (POST, PUT, DELETE)
    100 requests per day, 20 per hour
    """
    return limiter.limit("100 per day, 20 per hour")(f)


def api_auth_limit(f):
    """
    Strict rate limit for authentication endpoints
    10 requests per minute, 20 per hour
    Protects against brute force attacks
    """
    return limiter.limit("10 per minute, 20 per hour")(f)


def api_search_limit(f):
    """
    Rate limit for search endpoints
    60 requests per minute
    Search can be expensive, so we limit it more strictly
    """
    return limiter.limit("60 per minute")(f)


def api_export_limit(f):
    """
    Very strict rate limit for export operations
    10 requests per day, 2 per hour
    Exports are resource-intensive
    """
    return limiter.limit("10 per day, 2 per hour")(f)


def api_bulk_limit(f):
    """
    Rate limit for bulk operations
    20 requests per day, 5 per hour
    """
    return limiter.limit("20 per day, 5 per hour")(f)


# Custom rate limit error handler
def register_rate_limit_error_handler(app):
    """
    Register custom error handler for rate limit exceeded
    """
    from flask_limiter.errors import RateLimitExceeded

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(e):
        """Custom response when rate limit is exceeded"""
        return jsonify({
            'success': False,
            'message': 'Rate limit exceeded. Please try again later.',
            'error': 'rate_limit_exceeded'
        }), 429


# Role-based rate limiting
def admin_bypass(f):
    """
    Bypass rate limiting for admin users
    Use this decorator before rate limit decorators
    """
    from flask_login import current_user

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_admin():
            # Admin bypass - don't apply rate limiting
            return f(*args, **kwargs)
        # Apply normal function
        return f(*args, **kwargs)

    return decorated_function


# Endpoint-specific rate limit configurations
RATE_LIMITS = {
    'auth': {
        'login': '5 per minute, 10 per hour',
        'logout': '60 per minute',
        'register': '3 per hour, 10 per day',
    },
    'api': {
        'list': '200 per day, 50 per hour',
        'detail': '300 per day, 100 per hour',
        'create': '100 per day, 20 per hour',
        'update': '200 per day, 30 per hour',
        'delete': '50 per day, 10 per hour',
        'search': '60 per minute',
        'export': '10 per day, 2 per hour',
        'bulk': '20 per day, 5 per hour',
    }
}


def get_rate_limit_for_endpoint(endpoint_type, action):
    """
    Get rate limit string for a specific endpoint type and action

    Args:
        endpoint_type: 'auth' or 'api'
        action: Specific action like 'login', 'list', 'create', etc.

    Returns:
        str: Rate limit string or None if not found
    """
    return RATE_LIMITS.get(endpoint_type, {}).get(action)


# Example usage in blueprints:
"""
from app.utils.rate_limit_helpers import (
    api_standard_limit,
    api_write_limit,
    api_auth_limit,
    api_search_limit,
    api_export_limit
)

@bp.route('/items')
@api_standard_limit
@login_required
def list_items():
    # Your code here
    pass

@bp.route('/items', methods=['POST'])
@api_write_limit
@login_required
def create_item():
    # Your code here
    pass

@bp.route('/auth/login')
@api_auth_limit
def login():
    # Your code here
    pass

@bp.route('/items/search')
@api_search_limit
@login_required
def search_items():
    # Your code here
    pass

@bp.route('/items/export')
@api_export_limit
@login_required
def export_items():
    # Your code here
    pass
"""
