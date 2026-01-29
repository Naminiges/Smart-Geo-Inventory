#!/bin/bash

# Smart Geo Inventory - Production Start Script
# This script starts the application with Gunicorn production server

# Set environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file with production configuration"
    exit 1
fi

# Start with Gunicorn using threaded configuration
echo "Starting Smart Geo Inventory with Gunicorn..."
echo "Configuration: gunicorn_threaded.conf.py"
echo ""

# Start Gunicorn
gunicorn -c gunicorn_threaded.conf.py run:app

# Or use the standard configuration:
# gunicorn -c gunicorn.conf.py run:app

# Or start with inline configuration:
# gunicorn -w 4 --threads 4 -b 0.0.0.0:5000 --timeout 30 --worker-class=gthread run:app
