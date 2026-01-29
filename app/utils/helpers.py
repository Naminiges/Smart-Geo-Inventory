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


def get_user_warehouse_id(user):
    """Helper function to get warehouse_id from UserWarehouse relationship"""
    from app.models.user import UserWarehouse

    if not user or not user.is_authenticated:
        return None

    if user.is_admin():
        return None  # Admin can access all warehouses

    # For warehouse_staff, get their assigned warehouse
    user_warehouse = UserWarehouse.query.filter_by(user_id=user.id).first()
    return user_warehouse.warehouse_id if user_warehouse else None


def get_dashboard_stats(warehouse_id=None):
    """Get dashboard statistics"""
    from app.models import Item, ItemDetail, Stock, Warehouse, Unit, Distribution
    from app import db

    stats = {}

    # Network device counts - filter by item name containing keywords
    # Count ItemDetail (physical items like in items list)
    keywords = [
        ('access_point', 'access point'),
        ('server', 'server'),
        ('battery', ['battery', 'baterai']),
        ('switch', 'switch')
    ]

    for key, keyword in keywords:
        # Build filters for keyword(s)
        if isinstance(keyword, list):
            # Multiple keywords (e.g., battery/baterai)
            filters = [func.lower(Item.name).like(f'%{kw}%') for kw in keyword]
            keyword_filter = db.or_(*filters)
        else:
            # Single keyword
            keyword_filter = func.lower(Item.name).like(f'%{keyword}%')

        # Count from ItemDetail only (physical items)
        itemdetail_query = db.session.query(
            func.count(ItemDetail.id)
        ).join(
            Item, ItemDetail.item_id == Item.id
        ).filter(keyword_filter)

        itemdetail_count = itemdetail_query.scalar() or 0
        stats[f'{key}_count'] = itemdetail_count

    # Legacy stats for compatibility
    stats['total_items'] = Item.query.count()
    stats['total_categories'] = Item.query.with_entities(func.count(func.distinct(Item.category_id))).scalar()
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
    stats['broken_count'] = Distribution.query.filter(Distribution.status == 'broken').count()

    return stats


def get_warehouse_dashboard_stats(warehouse_id):
    """Get warehouse dashboard statistics for specific warehouse

    Args:
        warehouse_id: Warehouse ID to get stats for

    Returns:
        dict: Statistics including keyword-based item counts for that warehouse
    """
    from app.models import Item, ItemDetail, Stock
    from app import db

    stats = {}

    # Network device counts - filter by item name containing keywords
    # Count from Stock (warehouse inventory)
    keywords = [
        ('access_point', 'access point'),
        ('server', 'server'),
        ('battery', ['battery', 'baterai']),
        ('switch', 'switch')
    ]

    for key, keyword in keywords:
        # Build filters for keyword(s)
        if isinstance(keyword, list):
            # Multiple keywords (e.g., battery/baterai)
            filters = [func.lower(Item.name).like(f'%{kw}%') for kw in keyword]
            keyword_filter = db.or_(*filters)
        else:
            # Single keyword
            keyword_filter = func.lower(Item.name).like(f'%{keyword}%')

        # Count from Stock for this warehouse
        stock_query = db.session.query(
            func.sum(Stock.quantity)
        ).join(
            Item, Stock.item_id == Item.id
        ).filter(
            keyword_filter,
            Stock.warehouse_id == warehouse_id
        )

        stock_count = stock_query.scalar() or 0
        stats[f'{key}_count'] = stock_count

    return stats


def get_unit_dashboard_stats(unit_ids):
    """Get unit dashboard statistics for specific units

    Args:
        unit_ids: List of unit IDs to get stats for

    Returns:
        dict: Statistics including keyword-based item counts for those units
    """
    from app.models import Item, ItemDetail, Distribution, UnitDetail
    from app import db

    stats = {}

    # Network device counts - filter by item name containing keywords
    # Count ItemDetail (physical items) in the specified units only
    keywords = [
        ('access_point', 'access point'),
        ('server', 'server'),
        ('battery', ['battery', 'baterai']),
        ('switch', 'switch')
    ]

    for key, keyword in keywords:
        # Build filters for keyword(s)
        if isinstance(keyword, list):
            # Multiple keywords (e.g., battery/baterai)
            filters = [func.lower(Item.name).like(f'%{kw}%') for kw in keyword]
            keyword_filter = db.or_(*filters)
        else:
            # Single keyword
            keyword_filter = func.lower(Item.name).like(f'%{keyword}%')

        # Count from ItemDetail only, filtered by unit_id
        # Join Distribution to get unit_id, then filter by unit_ids
        itemdetail_query = db.session.query(
            func.count(ItemDetail.id)
        ).join(
            Item, ItemDetail.item_id == Item.id
        ).join(
            Distribution, ItemDetail.id == Distribution.item_detail_id
        ).filter(
            keyword_filter,
            Distribution.unit_id.in_(unit_ids)
        )

        itemdetail_count = itemdetail_query.scalar() or 0
        stats[f'{key}_count'] = itemdetail_count

    return stats


def get_admin_division_stats():
    """Get division statistics for admin dashboard

    Returns stats for the 4 main divisions: Jaringan, Server, Sistem Informasi, Perlengkapan Umum

    Returns:
        list: List of dicts containing unit info and item counts
    """
    from app.models import Unit, Item, ItemDetail, Distribution
    from app import db

    # Define the 4 main divisions to track
    # These will match by name keywords in Unit.name
    divisions = [
        {'name': 'Jaringan', 'keywords': ['jaringan', 'network'], 'icon': 'fa-network-wired', 'color': 'from-blue-500 to-blue-600'},
        {'name': 'Server', 'keywords': ['server'], 'icon': 'fa-server', 'color': 'from-purple-500 to-purple-600'},
        {'name': 'Sistem Informasi', 'keywords': ['sistem', 'informasi', 'si', 'ti'], 'icon': 'fa-laptop-code', 'color': 'from-emerald-500 to-emerald-600'},
        {'name': 'Perlengkapan Umum', 'keywords': ['perlengkapan', 'umum', 'general'], 'icon': 'fa-boxes', 'color': 'from-amber-500 to-amber-600'}
    ]

    result = []

    for division in divisions:
        # Find units that match the division keywords
        keyword_filters = [
            func.lower(Unit.name).like(f'%{kw}%')
            for kw in division['keywords']
        ]
        units = Unit.query.filter(db.or_(*keyword_filters)).all()

        if not units:
            # No units found for this division, skip
            continue

        unit_ids = [u.id for u in units]

        # Count items distributed to these units (excluding returned)
        # Count from Distribution where item_detail is not returned
        item_count = db.session.query(
            func.count(Distribution.id)
        ).join(
            ItemDetail, Distribution.item_detail_id == ItemDetail.id
        ).filter(
            Distribution.unit_id.in_(unit_ids),
            ItemDetail.status != 'returned'
        ).scalar() or 0

        # Use first unit for link (or could show all)
        primary_unit = units[0]

        result.append({
            'name': division['name'],
            'unit_id': primary_unit.id,
            'icon': division['icon'],
            'color': division['color'],
            'count': item_count,
            'units': units  # List of all units in this division
        })

    return result


def notification_counts():
    """Context processor to provide notification counts to templates"""
    from flask_login import current_user
    # Check if current_user exists and is authenticated
    if not current_user or not current_user.is_authenticated:
        return {
            'pending_request_count': 0,
            'verified_request_count': 0,
            'draft_distribution_count': 0,
            'pending_distribution_count': 0,
            'pending_procurement_count': 0
        }

    from app.models import AssetRequest, UserUnit, Distribution, DistributionGroup, Procurement

    counts = {
        'pending_request_count': 0,
        'verified_request_count': 0,
        'draft_distribution_count': 0,
        'pending_distribution_count': 0,
        'pending_procurement_count': 0
    }

    try:
        if current_user.is_admin():
            # ADMIN NOTIFICATIONS

            # 1. Permohonan Unit: Status 'pending' (menunggu verifikasi admin)
            counts['pending_request_count'] = AssetRequest.query.filter_by(status='pending').count()

            # 2. Procurement: Status 'pending' (menunggu persetujuan admin)
            pending_proc = Procurement.query.filter_by(status='pending').count()
            counts['pending_procurement_count'] = pending_proc
            print(f"DEBUG Admin {current_user.name}: pending_procurement_count={pending_proc}")

            # 3. Distribusi Langsung: Draft batch yang is_draft=True (menunggu verifikasi admin)
            counts['draft_distribution_count'] = DistributionGroup.query.filter_by(is_draft=True).count()

            # Admin tidak butuh notifikasi 'verified_request_count' dan 'pending_distribution_count'
            counts['verified_request_count'] = 0
            counts['pending_distribution_count'] = 0

        elif current_user.is_warehouse_staff():
            # WAREHOUSE STAFF NOTIFICATIONS
            from app.models.user import UserWarehouse

            # Get warehouse from UserWarehouse relationship
            user_warehouse = UserWarehouse.query.filter_by(user_id=current_user.id).first()

            if user_warehouse:
                # Warehouse staff hanya melihat:
                # 1. Distribusi Langsung: Draft batch dari warehouse mereka (is_draft=True)
                counts['draft_distribution_count'] = DistributionGroup.query.filter_by(
                    warehouse_id=user_warehouse.warehouse_id,
                    is_draft=True
                ).count()

                # 2. Procurement: Status 'approved' (siap diterima)
                approved_procurements = Procurement.query.filter_by(status='approved').count()
                counts['pending_procurement_count'] = approved_procurements
                print(f"DEBUG Warehouse Staff {current_user.name}: approved_procurement_count={approved_procurements}")
            else:
                # If no warehouse assigned, no notifications
                counts['draft_distribution_count'] = 0
                counts['pending_procurement_count'] = 0

            # Warehouse staff tidak butuh notifikasi lain
            counts['pending_request_count'] = 0
            counts['verified_request_count'] = 0
            counts['pending_distribution_count'] = 0

        elif current_user.is_unit_staff():
            # UNIT STAFF NOTIFICATIONS

            # Get user's assigned units
            user_unit_ids = [uu.unit_id for uu in UserUnit.query.filter_by(user_id=current_user.id).all()]

            if user_unit_ids:
                # 1. Permohonan Unit: Status 'pending' (menunggu verifikasi admin) - untuk sidebar "Daftar Permohonan"
                pending_reqs = AssetRequest.query.filter(
                    AssetRequest.unit_id.in_(user_unit_ids),
                    AssetRequest.status == 'pending'
                ).all()
                counts['pending_request_count'] = len(pending_reqs)

                # Debug: print hasil
                print(f"DEBUG Unit Staff {current_user.name}: unit_ids={user_unit_ids}, pending_count={counts['pending_request_count']}")

                # 2. Permohonan Unit: Status 'verified' (siap didistribusikan warehouse)
                counts['verified_request_count'] = AssetRequest.query.filter(
                    AssetRequest.unit_id.in_(user_unit_ids),
                    AssetRequest.status == 'verified'
                ).count()

                # 3. Terima Distribusi: Batch approved yang siap diterima
                # (verification_status='pending', status in 'installing'/'in_transit')
                counts['pending_distribution_count'] = DistributionGroup.query.filter(
                    DistributionGroup.is_draft == False,
                    DistributionGroup.status == 'approved'
                ).join(Distribution).filter(
                    Distribution.unit_id.in_(user_unit_ids),
                    Distribution.verification_status == 'pending',
                    Distribution.status.in_(['installing', 'in_transit'])
                ).distinct().count()

            # Unit staff tidak butuh notifikasi draft_distribution_count dan pending_procurement_count
            counts['draft_distribution_count'] = 0
            counts['pending_procurement_count'] = 0

    except Exception as e:
        import traceback
        traceback.print_exc()
        counts['pending_request_count'] = 0
        counts['verified_request_count'] = 0
        counts['draft_distribution_count'] = 0
        counts['pending_distribution_count'] = 0
        counts['pending_procurement_count'] = 0

    return counts
