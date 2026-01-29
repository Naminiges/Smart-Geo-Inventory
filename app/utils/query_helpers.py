"""
Query helper utilities to reduce code duplication
Centralizes common query patterns across the application
"""

from flask_login import current_user
from app import db
from app.models import Item, Category, UserWarehouse, UserUnit


def get_user_warehouse_query(model_class):
    """
    Get a query filtered by user's warehouse access
    Centralizes the repeated pattern of filtering by user warehouse

    Args:
        model_class: SQLAlchemy model class to query

    Returns:
        SQLAlchemy query object filtered by user's warehouse access
    """
    query = model_class.query

    # Filter by warehouse for non-admin users
    if current_user.is_authenticated and not current_user.is_admin():
        if hasattr(model_class, 'warehouse_id'):
            # Model has warehouse_id column
            if current_user.is_warehouse_staff():
                user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
                if user_warehouse_ids:
                    query = query.filter(model_class.warehouse_id.in_(user_warehouse_ids))
                else:
                    # No warehouse access - return empty query
                    query = query.filter(model_class.warehouse_id == -1)

    return query


def get_user_unit_query(model_class):
    """
    Get a query filtered by user's unit access
    Centralizes the repeated pattern of filtering by user unit

    Args:
        model_class: SQLAlchemy model class to query

    Returns:
        SQLAlchemy query object filtered by user's unit access
    """
    query = model_class.query

    # Filter by unit for unit staff
    if current_user.is_authenticated and current_user.is_unit_staff():
        if hasattr(model_class, 'unit_id'):
            # Model has unit_id column
            user_unit_ids = [uu.unit_id for uu in current_user.user_units.all()]
            if user_unit_ids:
                query = query.filter(model_class.unit_id.in_(user_unit_ids))
            else:
                # No unit access - return empty query
                query = query.filter(model_class.unit_id == -1)

    return query


def get_form_choices_cache():
    """
    Get form choices with caching
    Returns cached choices for items, categories, and suppliers

    Returns:
        dict: Form choices for dropdowns
    """
    from app.utils.cache_helpers import get_form_choices
    return get_form_choices()


def get_item_choices():
    """Get item choices for forms"""
    from app.utils.cache_helpers import get_form_choices
    choices = get_form_choices_cache()
    return choices.get('items', [])


def get_category_choices():
    """Get category choices for forms"""
    from app.utils.cache_helpers import get_form_choices
    choices = get_form_choices_cache()
    return choices.get('categories', [])


def get_supplier_choices():
    """Get supplier choices for forms"""
    from app.utils.cache_helpers import get_form_choices
    choices = get_form_choices_cache()
    return choices.get('suppliers', [])


def apply_pagination(query, page=1, per_page=20):
    """
    Apply pagination to a query
    Centralizes pagination logic

    Args:
        query: SQLAlchemy query object
        page: Page number (default: 1)
        per_page: Items per page (default: 20)

    Returns:
        Pagination object
    """
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )


def get_dashboard_statistics_cached():
    """
    Get dashboard statistics with caching
    Reduces database queries for dashboard

    Returns:
        dict: Dashboard statistics
    """
    from app.utils.cache_helpers import get_dashboard_stats
    return get_dashboard_stats()


def invalidate_related_caches(model_instance):
    """
    Invalidate caches related to a model instance
    Call this after creating/updating/deleting records

    Args:
        model_instance: Model instance that was modified
    """
    from app.utils.cache_helpers import (
        invalidate_form_choices,
        invalidate_dashboard_stats
    )

    model_name = model_instance.__class__.__name__

    # Invalidate form choices cache
    if model_name in ['Item', 'Category']:
        invalidate_form_choices()

    # Invalidate dashboard stats
    if model_name in ['Item', 'Stock', 'Procurement', 'Distribution', 'Warehouse']:
        invalidate_dashboard_stats()


def get_user_warehouse_ids_cached(user):
    """
    Get user warehouse IDs with caching
    Reduces repeated queries for user warehouse access

    Args:
        user: User object

    Returns:
        list: List of warehouse IDs
    """
    from app.utils.cache_helpers import get_user_warehouse_ids
    return get_user_warehouse_ids(user)


def get_user_unit_ids_cached(user):
    """
    Get user unit IDs with caching
    Reduces repeated queries for user unit access

    Args:
        user: User object

    Returns:
        list: List of unit IDs
    """
    # Similar to get_user_warehouse_ids_cached
    # Can be added to cache_helpers.py
    return [uu.unit_id for uu in user.user_units.all()]


def with_eager_loading(query, *relations):
    """
    Apply eager loading to a query to prevent N+1 problems

    Args:
        query: SQLAlchemy query object
        *relations: List of relationship names to eager load

    Returns:
        Query with eager loading applied
    """
    for relation in relations:
        query = query.options(db.joinedload(relation))
    return query


def search_items(query, search_term):
    """
    Apply search filter to item query
    Centralizes search logic

    Args:
        query: SQLAlchemy query object
        search_term: Search term string

    Returns:
        Filtered query
    """
    if search_term:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Item.name.ilike(f'%{search_term}%'),
                Item.item_code.ilike(f'%{search_term}%')
            )
        )
    return query
