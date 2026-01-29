"""
WSGI entry point for Smart Geo Inventory
This file is used by Gunicorn to start the application
"""

import os
from app import create_app

# Create Flask app instance
app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    app.run()
