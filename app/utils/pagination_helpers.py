"""
Pagination helper utilities for API endpoints.
Provides consistent pagination across all list endpoints.
"""

from flask import request
from sqlalchemy import inspect
from sqlalchemy.orm import joinedload


class PaginatedResponse:
    """Helper class for paginated API responses"""

    def __init__(self, query, page=None, per_page=None, max_per_page=100):
        """
        Initialize paginated response

        Args:
            query: SQLAlchemy query object
            page: Page number (default from request args)
            per_page: Items per page (default from request args)
            max_per_page: Maximum items per page (default 100)
        """
        self.query = query
        self.page = page or request.args.get('page', 1, type=int)
        self.per_page = per_page or request.args.get('per_page', 20, type=int)
        self.max_per_page = max_per_page

        # Validate pagination parameters
        if self.page < 1:
            self.page = 1
        if self.per_page < 1:
            self.per_page = 20
        if self.per_page > self.max_per_page:
            self.per_page = self.max_per_page

    def paginate(self):
        """Execute pagination and return result"""
        pagination = self.query.paginate(
            page=self.page,
            per_page=self.per_page,
            error_out=False
        )

        return {
            'success': True,
            'data': [item.to_dict() for item in pagination.items],
            'pagination': {
                'page': self.page,
                'per_page': self.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_page': pagination.next_num if pagination.has_next else None,
                'prev_page': pagination.prev_num if pagination.has_prev else None,
            }
        }

    def paginate_with_relations(self, *relations):
        """
        Execute pagination with eager loaded relations

        Args:
            *relations: List of relationship names to eager load
        """
        # Apply eager loading
        for relation in relations:
            self.query = self.query.options(joinedload(relation))

        return self.paginate()


def paginated_response(query, serializer=None, max_per_page=100):
    """
    Decorator/function to create paginated API responses

    Args:
        query: SQLAlchemy query object
        serializer: Optional serializer function (uses to_dict() if not provided)
        max_per_page: Maximum items per page

    Returns:
        dict: Paginated response
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > max_per_page:
        per_page = max_per_page

    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Serialize data
    if serializer:
        data = [serializer(item) for item in pagination.items]
    else:
        data = [item.to_dict() for item in pagination.items]

    return {
        'success': True,
        'data': data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_page': pagination.next_num if pagination.has_next else None,
            'prev_page': pagination.prev_num if pagination.has_prev else None,
        }
    }


def get_pagination_params(default_per_page=20, max_per_page=100):
    """
    Get and validate pagination parameters from request

    Returns:
        tuple: (page, per_page)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = default_per_page
    if per_page > max_per_page:
        per_page = max_per_page

    return page, per_page


def build_meta_pagination(pagination):
    """
    Build pagination metadata from SQLAlchemy pagination object

    Args:
        pagination: SQLAlchemy pagination object

    Returns:
        dict: Pagination metadata
    """
    return {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_page': pagination.next_num if pagination.has_next else None,
        'prev_page': pagination.prev_num if pagination.has_prev else None,
    }
