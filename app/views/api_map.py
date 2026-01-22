from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from geoalchemy2.functions import ST_AsGeoJSON
from app import db
from app.models import Warehouse, Unit, Distribution, ItemDetail
from app.utils.helpers import get_user_warehouse_id

bp = Blueprint('api_map', __name__)


@bp.route('/warehouses')
@login_required
def api_warehouses():
    """Get all warehouses as GeoJSON"""
    # Query warehouses with geometry
    warehouses = Warehouse.query.all()

    features = []
    for warehouse in warehouses:
        if warehouse.geom:
            # Convert geometry to GeoJSON
            geojson = db.session.query(
                ST_AsGeoJSON(Warehouse.geom)
            ).filter(Warehouse.id == warehouse.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(warehouse.geom), func.ST_Y(warehouse.geom))
            ).first()

            features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': warehouse.id,
                    'name': warehouse.name,
                    'address': warehouse.address,
                    'type': 'warehouse',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })


@bp.route('/units')
@login_required
def api_units():
    """Get all units as GeoJSON"""
    units = Unit.query.all()

    features = []
    for unit in units:
        if unit.geom:
            geojson = db.session.query(
                ST_AsGeoJSON(Unit.geom)
            ).filter(Unit.id == unit.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(unit.geom), func.ST_Y(unit.geom))
            ).first()

            features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': unit.id,
                    'name': unit.name,
                    'address': unit.address,
                    'type': 'unit',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })


@bp.route('/distributions')
@login_required
def api_distributions():
    """Get all distributions as GeoJSON"""
    # Filter by user role
    if current_user.is_warehouse_staff():
        distributions = Distribution.query.filter(
            Distribution.warehouse_id == get_user_warehouse_id(current_user)
        ).all()
    elif current_user.is_field_staff():
        distributions = Distribution.query.filter(
            Distribution.field_staff_id == current_user.id
        ).all()
    else:  # admin
        distributions = Distribution.query.all()

    features = []
    for distribution in distributions:
        if distribution.geom:
            geojson = db.session.query(
                ST_AsGeoJSON(Distribution.geom)
            ).filter(Distribution.id == distribution.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(distribution.geom), func.ST_Y(distribution.geom))
            ).first()

            features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': distribution.id,
                    'serial_number': distribution.item_detail.serial_number if distribution.item_detail else None,
                    'item_name': distribution.item_detail.item.name if distribution.item_detail else None,
                    'status': distribution.status,
                    'address': distribution.address,
                    'type': 'distribution',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })


@bp.route('/all')
@login_required
def api_all():
    """Get all features (warehouses, units, distributions) as GeoJSON"""
    # Get warehouse features
    warehouse_features = []
    warehouses = Warehouse.query.all()
    for warehouse in warehouses:
        if warehouse.geom:
            geojson = db.session.query(
                ST_AsGeoJSON(Warehouse.geom)
            ).filter(Warehouse.id == warehouse.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(warehouse.geom), func.ST_Y(warehouse.geom))
            ).first()

            warehouse_features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': warehouse.id,
                    'name': warehouse.name,
                    'address': warehouse.address,
                    'layer': 'warehouse',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    # Get unit features
    unit_features = []
    units = Unit.query.all()
    for unit in units:
        if unit.geom:
            geojson = db.session.query(
                ST_AsGeoJSON(Unit.geom)
            ).filter(Unit.id == unit.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(unit.geom), func.ST_Y(unit.geom))
            ).first()

            unit_features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': unit.id,
                    'name': unit.name,
                    'address': unit.address,
                    'layer': 'unit',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    # Get distribution features
    distribution_features = []
    if current_user.is_admin():
        distributions = Distribution.query.all()
    elif current_user.is_warehouse_staff():
        distributions = Distribution.query.filter(
            Distribution.warehouse_id == get_user_warehouse_id(current_user)
        ).all()
    else:
        distributions = Distribution.query.filter(
            Distribution.field_staff_id == current_user.id
        ).all()

    for distribution in distributions:
        if distribution.geom:
            geojson = db.session.query(
                ST_AsGeoJSON(Distribution.geom)
            ).filter(Distribution.id == distribution.id).scalar()

            coords = db.session.execute(
                db.select(func.ST_X(distribution.geom), func.ST_Y(distribution.geom))
            ).first()

            distribution_features.append({
                'type': 'Feature',
                'geometry': eval(geojson) if geojson else None,
                'properties': {
                    'id': distribution.id,
                    'serial_number': distribution.item_detail.serial_number if distribution.item_detail else None,
                    'item_name': distribution.item_detail.item.name if distribution.item_detail else None,
                    'status': distribution.status,
                    'address': distribution.address,
                    'layer': 'distribution',
                    'latitude': float(coords[1]) if coords else None,
                    'longitude': float(coords[0]) if coords else None
                }
            })

    # Combine all features
    all_features = warehouse_features + unit_features + distribution_features

    return jsonify({
        'type': 'FeatureCollection',
        'features': all_features
    })


@bp.route('/nearby', methods=['GET'])
@login_required
def api_nearby():
    """Get nearby features within radius"""
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lng', type=float)
    radius_km = request.args.get('radius', 5, type=float)  # Default 5km

    if not latitude or not longitude:
        return jsonify({'success': False, 'message': 'Latitude and longitude required'}), 400

    from geoalchemy2.functions import ST_Distance_Sphere, ST_MakePoint, ST_SetSRID
    from sqlalchemy import cast, Float

    # Create point from coordinates
    point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    # Get nearby warehouses
    nearby_warehouses = db.session.query(
        Warehouse,
        cast(ST_Distance_Sphere(Warehouse.geom, point) / 1000, Float).label('distance')
    ).filter(
        ST_Distance_Sphere(Warehouse.geom, point) <= radius_km * 1000
    ).all()

    warehouse_data = [{'id': w.id, 'name': w.name, 'distance_km': distance} for w, distance in nearby_warehouses]

    # Get nearby units
    nearby_units = db.session.query(
        Unit,
        cast(ST_Distance_Sphere(Unit.geom, point) / 1000, Float).label('distance')
    ).filter(
        ST_Distance_Sphere(Unit.geom, point) <= radius_km * 1000
    ).all()

    unit_data = [{'id': u.id, 'name': u.name, 'distance_km': distance} for u, distance in nearby_units]

    return jsonify({
        'success': True,
        'warehouses': warehouse_data,
        'units': unit_data
    })
