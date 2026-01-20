from flask import send_file
import math
from geoalchemy2.functions import ST_Distance_Sphere
from sqlalchemy import func
from flask_login import current_user


def generate_barcode(code, barcode_type='code128'):
    """Generate barcode image from code"""
    # TODO: Implement barcode generation when compatible package available
    # For now, return placeholder
    raise NotImplementedError("Barcode generation not yet implemented for Python 3.13")


def send_notification(user, message, notification_type='info'):
    """Send notification to user (placeholder for future implementation)"""
    # This can be integrated with email, SMS, or in-app notification system
    # For now, we'll just flash a message
    from flask import flash
    flash(message, notification_type)


def calculate_distance(geom1, geom2):
    """Calculate distance between two geometries in meters using Haversine formula"""
    try:
        # This requires PostGIS ST_Distance_Sphere function
        from app import db
        result = db.session.query(
            ST_Distance_Sphere(geom1, geom2)
        ).scalar()
        return result
    except Exception as e:
        raise Exception(f'Error calculating distance: {str(e)}')


def calculate_bounding_box(center_lat, center_lon, radius_km):
    """Calculate bounding box for GIS queries"""
    # Earth radius in km
    earth_radius = 6371.0

    # Calculate delta for latitude and longitude
    delta_lat = (radius_km / earth_radius) * (180 / math.pi)
    delta_lon = (radius_km / earth_radius) * (180 / math.pi) / math.cos(math.radians(center_lat))

    return {
        'min_lat': center_lat - delta_lat,
        'max_lat': center_lat + delta_lat,
        'min_lon': center_lon - delta_lon,
        'max_lon': center_lon + delta_lon
    }


def format_geojson_feature(geom, properties):
    """Format geometry and properties into GeoJSON feature"""
    from geoalchemy2.functions import ST_AsGeoJSON
    from app import db

    # Convert geometry to GeoJSON
    geojson = db.session.query(ST_AsGeoJSON(geom)).scalar()

    return {
        'type': 'Feature',
        'geometry': geojson,
        'properties': properties
    }


def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        from flask import current_app
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_low_stock_items(threshold=10):
    """Get items with stock below threshold"""
    from app.models import Stock
    return Stock.query.filter(Stock.quantity < threshold).all()


def get_dashboard_stats(warehouse_id=None):
    """Get dashboard statistics"""
    from app.models import Item, ItemDetail, Stock, Warehouse, Unit, Distribution
    from app import db

    stats = {}

    # Total items and categories
    stats['total_items'] = Item.query.count()
    stats['total_categories'] = Item.query.with_entities(func.count(func.distinct(Item.category_id))).scalar()

    # Total warehouses and units
    stats['total_warehouses'] = Warehouse.query.count()
    stats['total_units'] = Unit.query.count()

    # Stock information
    stock_query = db.session.query(func.sum(Stock.quantity))
    if warehouse_id:
        stock_query = stock_query.filter(Stock.warehouse_id == warehouse_id)
    stats['total_stock'] = stock_query.scalar() or 0

    # Low stock items
    low_stock_query = Stock.query.filter(Stock.quantity < 10)
    if warehouse_id:
        low_stock_query = low_stock_query.filter(Stock.warehouse_id == warehouse_id)
    stats['low_stock_count'] = low_stock_query.count()

    # Item details by status
    item_detail_query = ItemDetail.query
    if warehouse_id:
        item_detail_query = item_detail_query.filter(ItemDetail.warehouse_id == warehouse_id)

    stats['available_items'] = item_detail_query.filter(ItemDetail.status == 'available').count()
    stats['used_items'] = item_detail_query.filter(ItemDetail.status == 'used').count()
    stats['maintenance_items'] = item_detail_query.filter(ItemDetail.status == 'maintenance').count()

    # Distribution status
    stats['installing_count'] = Distribution.query.filter(Distribution.status == 'installing').count()
    stats['installed_count'] = Distribution.query.filter(Distribution.status == 'installed').count()

    return stats


def notification_counts():
    """Context processor to provide notification counts to templates"""
    if not current_user.is_authenticated:
        return {'pending_request_count': 0}

    from app.models import AssetRequest, UserUnit

    counts = {'pending_request_count': 0}

    try:
        if current_user.is_admin():
            # Admin sees all pending requests
            counts['pending_request_count'] = AssetRequest.query.filter_by(status='pending').count()
        elif current_user.is_unit_staff():
            # Unit staff sees pending requests for their assigned units
            user_unit_ids = [uu.unit_id for uu in UserUnit.query.filter_by(user_id=current_user.id).all()]
            if user_unit_ids:
                counts['pending_request_count'] = AssetRequest.query.filter(
                    AssetRequest.unit_id.in_(user_unit_ids),
                    AssetRequest.status == 'pending'
                ).count()
    except Exception:
        counts['pending_request_count'] = 0

    return counts
