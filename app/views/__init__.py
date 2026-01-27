# Blueprint imports
from app.views.auth import bp
from app.views.dashboard import bp
from app.views.installations import bp
from app.views.stock import bp
from app.views.items import bp
from app.views.map import bp
from app.views.procurement import bp
from app.views.users import bp
from app.views.categories import bp
from app.views.admin.buildings import bp as admin_buildings_bp

# API blueprint imports
from app.views.api_auth import bp
from app.views.api_dashboard import bp
from app.views.api_installations import bp
from app.views.api_stock import bp
from app.views.api_items import bp
from app.views.api_map import bp
from app.views.api_procurement import bp
