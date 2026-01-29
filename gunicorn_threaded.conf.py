"""
Gunicorn configuration with threading for better concurrency
Use this for I/O bound operations like database queries
"""

import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes with threading
# Fewer workers but more threads per worker
workers = max(2, multiprocessing.cpu_count())  # At least 2 workers
worker_class = "gthread"  # Use threads for better I/O concurrency
threads = 4  # Number of threads per worker
worker_connections = 1000

# Request handling
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Process naming
proc_name = "smart_geo_inventory_threaded"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process management
daemon = False

def when_ready(server):
    """Called just after the server is started."""
    print(f"Smart Geo Inventory server ready with {workers} workers and {threads} threads each")
    print(f"Total concurrent capacity: {workers * threads} threads")
