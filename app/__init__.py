from flask import Flask, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# from flask_session import Session  # DISABLED - Use default Flask session instead
from config.config import config
from app.utils.datetime_helper import format_wib_datetime
from app.utils.status_helper import translate_status, get_status_color, get_status_icon
from app.utils.mail_helper import SSLMail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cors = CORS()
csrf = CSRFProtect()
cache = Cache()
# server_session = Session()  # DISABLED - Not using Flask-Session
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"],  # Increased for benchmarking
    storage_uri="memory://"
)
mail = SSLMail()


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
    cache.init_app(app)
    # Flask-Session DISABLED - Using default Flask client-side session
    # server_session.init_app(app)  # DISABLED
    limiter.init_app(app)
    mail.init_app(app)

    # Register rate limit error handler
    from app.utils.rate_limit_helpers import register_rate_limit_error_handler
    register_rate_limit_error_handler(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'

    # Register custom Jinja2 filters
    app.jinja_env.filters['format_wib_datetime'] = format_wib_datetime
    app.jinja_env.filters['translate_status'] = translate_status
    app.jinja_env.filters['get_status_color'] = get_status_color
    app.jinja_env.filters['get_status_icon'] = get_status_icon

    # Register context processors
    from app.utils.helpers import notification_counts

    # Make helpers available in all templates
    @app.context_processor
    def utility_helpers():
        data = notification_counts()
        # CSRF token is automatically handled by Flask-WTF's form.hidden_tag()
        return data

    # CSRF error handler
    @app.errorhandler(400)
    def handle_csrf_error(e):
        from flask import render_template
        if 'CSRF' in str(e):
            import logging
            logging.error(f"CSRF Error: {e}")
            logging.error(f"Session data: {session}")
            return render_template('errors/csrf_error.html', error=str(e)), 400
        return e

    # Register blueprints
    from app.views import main, auth, dashboard, installations, stock, items, map, procurement, users, categories, asset_requests, units, field_tasks, unit_procurement, asset_loans, distributions, returns, venue_loans, warehouses, buildings, asset_transfer
    from app.views.admin import buildings as admin_buildings
    from app.views import api_auth, api_dashboard, api_installations, api_stock, api_items, api_map, api_procurement, api_units, api_unit_procurement

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(installations.bp)
    app.register_blueprint(stock.bp)
    app.register_blueprint(items.bp)
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
    app.register_blueprint(returns.bp)
    app.register_blueprint(venue_loans.bp)
    app.register_blueprint(warehouses.bp)
    app.register_blueprint(buildings.bp)
    app.register_blueprint(admin_buildings.bp)
    app.register_blueprint(asset_transfer.bp)

    # Register API blueprints
    app.register_blueprint(api_auth.bp, url_prefix='/api/auth')
    app.register_blueprint(api_dashboard.bp, url_prefix='/api/dashboard')
    app.register_blueprint(api_installations.bp, url_prefix='/api/installations')
    app.register_blueprint(api_stock.bp, url_prefix='/api/stock')
    app.register_blueprint(api_items.bp, url_prefix='/api/items')
    app.register_blueprint(api_map.bp, url_prefix='/api/map')
    app.register_blueprint(api_procurement.bp, url_prefix='/api')
    app.register_blueprint(api_units.bp)
    app.register_blueprint(api_unit_procurement.bp, url_prefix='/api')

    # Create tables - DISABLED in production to prevent connection overflow
    # Tables should be created manually using migrations or seed scripts
    # with app.app_context():
    #     db.create_all()

    # Initialize background scheduler for venue loans
    from app.scheduler import init_scheduler
    init_scheduler(app)

    return app
