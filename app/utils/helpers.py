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
    stats['low_stock_items'] = low_stock_query.order_by(Stock.quantity.asc()).all()

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
        return {
            'pending_request_count': 0,
            'verified_request_count': 0,
            'draft_distribution_count': 0,
            'pending_distribution_count': 0
        }

    from app.models import AssetRequest, UserUnit, Distribution, DistributionGroup

    counts = {
        'pending_request_count': 0,
        'verified_request_count': 0,
        'draft_distribution_count': 0,
        'pending_distribution_count': 0
    }

    try:
        if current_user.is_admin():
            # ADMIN NOTIFICATIONS

            # 1. Permohonan Unit: Status 'pending' (menunggu verifikasi admin)
            counts['pending_request_count'] = AssetRequest.query.filter_by(status='pending').count()

            # 2. Distribusi Langsung: Draft batch yang is_draft=True (menunggu verifikasi admin)
            counts['draft_distribution_count'] = DistributionGroup.query.filter_by(is_draft=True).count()

            # Admin tidak butuh notifikasi 'verified_request_count' dan 'pending_distribution_count'
            counts['verified_request_count'] = 0
            counts['pending_distribution_count'] = 0

        elif current_user.is_warehouse_staff():
            # WAREHOUSE STAFF NOTIFICATIONS

            # Warehouse staff hanya melihat:
            # 1. Distribusi Langsung: Draft batch dari warehouse mereka (is_draft=True)
            counts['draft_distribution_count'] = DistributionGroup.query.filter_by(
                warehouse_id=current_user.warehouse_id,
                is_draft=True
            ).count()

            # Warehouse staff tidak butuh notifikasi lain
            counts['pending_request_count'] = 0
            counts['verified_request_count'] = 0
            counts['pending_distribution_count'] = 0

        elif current_user.is_unit_staff():
            # UNIT STAFF NOTIFICATIONS

            # Get user's assigned units
            user_unit_ids = [uu.unit_id for uu in UserUnit.query.filter_by(user_id=current_user.id).all()]

            if user_unit_ids:
                # 1. Permohonan Unit: Status 'verified' (siap didistribusikan warehouse)
                counts['verified_request_count'] = AssetRequest.query.filter(
                    AssetRequest.unit_id.in_(user_unit_ids),
                    AssetRequest.status == 'verified'
                ).count()

                # 2. Terima Distribusi: Batch approved yang siap diterima
                # (verification_status='pending', status in 'installing'/'in_transit')
                counts['pending_distribution_count'] = DistributionGroup.query.filter(
                    DistributionGroup.is_draft == False,
                    DistributionGroup.status == 'approved'
                ).join(Distribution).filter(
                    Distribution.unit_id.in_(user_unit_ids),
                    Distribution.verification_status == 'pending',
                    Distribution.status.in_(['installing', 'in_transit'])
                ).distinct().count()

            # Unit staff tidak butuh notifikasi pending_request_count dan draft_distribution_count
            counts['pending_request_count'] = 0
            counts['draft_distribution_count'] = 0

    except Exception as e:
        import traceback
        traceback.print_exc()
        counts['pending_request_count'] = 0
        counts['verified_request_count'] = 0
        counts['draft_distribution_count'] = 0
        counts['pending_distribution_count'] = 0

    return counts
