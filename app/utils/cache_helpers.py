"""
Cache helper utilities for frequently accessed data.
Reduces database queries and improves performance.
"""

from functools import wraps
from flask import current_app
from app import cache


def cache_frequently_accessed(timeout=None):
    """
    Decorator to cache frequently accessed data.
    Default timeout is 5 minutes (300 seconds).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{f.__name__}_{str(args)}_{str(kwargs)}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = f(*args, **kwargs)
            cache_timeout = timeout or current_app.config['CACHE_DEFAULT_TIMEOUT']
            cache.set(cache_key, result, timeout=cache_timeout)

            return result
        return decorated_function
    return decorator


def clear_cache_pattern(pattern):
    """
    Clear all cache keys matching a pattern.
    Useful when data is updated.
    """
    # Note: This requires Redis backend to work efficiently
    # For SimpleCache, we'll just clear everything
    try:
        cache.clear()
    except Exception:
        pass


def get_user_warehouse_ids(user):
    """
    Get user warehouse IDs with caching.
    This is one of the most frequently accessed patterns.
    """
    cache_key = f"user_warehouses_{user.id}"

    cached_ids = cache.get(cache_key)
    if cached_ids is not None:
        return cached_ids

    warehouse_ids = [uw.warehouse_id for uw in user.user_warehouses.all()]
    cache.set(cache_key, warehouse_ids, timeout=300)

    return warehouse_ids


def invalidate_user_warehouses(user_id):
    """Invalidate cached warehouse IDs for a user."""
    cache.delete(f"user_warehouses_{user_id}")


def get_form_choices():
    """
    Get common form choices with caching.
    Reduces repetitive queries for items, categories, suppliers.
    """
    cache_key = "form_choices_all"

    cached_choices = cache.get(cache_key)
    if cached_choices is not None:
        return cached_choices

    from app.models import Item, Category, Supplier

    choices = {
        'items': [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()],
        'categories': [(c.id, c.name) for c in Category.query.all()],
        'suppliers': [(s.id, s.name) for s in Supplier.query.all()],
    }

    cache.set(cache_key, choices, timeout=300)

    return choices


def invalidate_form_choices():
    """Invalidate cached form choices."""
    cache.delete("form_choices_all")


def get_dashboard_stats():
    """
    Get dashboard statistics with caching.
    Dashboard is accessed frequently but data changes slowly.
    """
    cache_key = "dashboard_stats"

    cached_stats = cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    from app.models import Item, Warehouse, Procurement, Distribution

    stats = {
        'total_items': Item.query.count(),
        'total_warehouses': Warehouse.query.count(),
        'pending_procurements': Procurement.query.filter_by(status='pending').count(),
        'active_distributions': Distribution.query.filter_by(status='in_transit').count(),
    }

    cache.set(cache_key, stats, timeout=60)  # Cache for 1 minute

    return stats


def invalidate_dashboard_stats():
    """Invalidate cached dashboard statistics."""
    cache.delete("dashboard_stats")
