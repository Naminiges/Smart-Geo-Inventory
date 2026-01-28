import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class with common settings"""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'security-salt'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost:5432/smart_geo_inventory'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging

    # Database Connection Pooling - Optimized for performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,              # Base pool size for concurrent connections
        'max_overflow': 30,           # Additional connections when pool is full
        'pool_timeout': 30,           # Timeout in seconds for getting connection
        'pool_recycle': 3600,         # Recycle connections every hour (prevent stale)
        'pool_pre_ping': True,        # Verify connections before using
        'echo_pool': False,           # Set to True for pool debugging
    }

    # Caching Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'SimpleCache'  # Use 'RedisCache' in production
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes default cache timeout
    CACHE_KEY_PREFIX = 'sgi_'    # Prefix for cache keys

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

    # Pagination
    ITEMS_PER_PAGE = 20

    # CORS
    CORS_HEADERS = 'Content-Type'

    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@sapapsi.com'

    # Application Settings
    APP_NAME = 'Smart Geo Inventory'
    APP_VERSION = '1.0.0'
    APP_DESCRIPTION = 'Sistem Manajemen Inventaris Geografis'

    # GIS Settings
    DEFAULT_MAP_CENTER = [3.561676, 98.6563423]  # Universitas Sumatera Utara
    DEFAULT_MAP_ZOOM = 13

    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        # Create upload folder if it doesn't exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Production-specific optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 30,              # Larger pool for production
        'max_overflow': 50,           # More overflow capacity
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Use Redis for caching in production
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 600  # 10 minutes for production


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@localhost:5432/smart_geo_inventory_test'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
