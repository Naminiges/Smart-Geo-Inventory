from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config.config import config
from app.utils.datetime_helper import format_wib_datetime

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cors = CORS()
csrf = CSRFProtect()


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    csrf.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'

    # Register custom Jinja2 filters
    app.jinja_env.filters['format_wib_datetime'] = format_wib_datetime

    # Register context processors
    from app.utils.helpers import notification_counts

    # Make helpers available in all templates
    @app.context_processor
    def utility_helpers():
        return notification_counts()

    # Register blueprints
    from app.views import auth, dashboard, installations, stock, items, suppliers, map, procurement, users, categories, asset_requests, units, field_tasks, unit_procurement, asset_loans, distributions
    from app.views import api_auth, api_dashboard, api_installations, api_stock, api_items, api_suppliers, api_map, api_procurement, api_units, api_unit_procurement

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(installations.bp)
    app.register_blueprint(stock.bp)
    app.register_blueprint(items.bp)
    app.register_blueprint(suppliers.bp)
    app.register_blueprint(map.bp)
    app.register_blueprint(procurement.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(asset_requests.bp)
    app.register_blueprint(units.bp)
    app.register_blueprint(field_tasks.bp)
    app.register_blueprint(unit_procurement.bp)
    app.register_blueprint(asset_loans.bp)
    app.register_blueprint(distributions.bp)

    # Register API blueprints
    app.register_blueprint(api_auth.bp, url_prefix='/api/auth')
    app.register_blueprint(api_dashboard.bp, url_prefix='/api/dashboard')
    app.register_blueprint(api_installations.bp, url_prefix='/api/installations')
    app.register_blueprint(api_stock.bp, url_prefix='/api/stock')
    app.register_blueprint(api_items.bp, url_prefix='/api/items')
    app.register_blueprint(api_suppliers.bp, url_prefix='/api/suppliers')
    app.register_blueprint(api_map.bp, url_prefix='/api/map')
    app.register_blueprint(api_procurement.bp, url_prefix='/api')
    app.register_blueprint(api_units.bp)
    app.register_blueprint(api_unit_procurement.bp, url_prefix='/api')

    # Root route - redirect to login or dashboard
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Create tables
    with app.app_context():
        db.create_all()

    return app
