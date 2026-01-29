"""
Gunicorn configuration file for Smart Geo Inventory
Optimized for performance and production use
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
# Reduced workers to prevent database connection overflow
workers = 2  # Start with 2 workers only
worker_class = "sync"  # Can use 'gevent' or 'gthread' for async workers
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 50  # Randomize restarts to prevent all workers restarting at once
timeout = 30  # Worker timeout in seconds
keepalive = 2  # Keep-alive connections

# Process naming
proc_name = "smart_geo_inventory"

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False  # Run in foreground (use with systemd/supervisord)
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if using HTTPS)
# keyfile = "/path/to/ssl/key.pem"
# certfile = "/path/to/ssl/cert.pem"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("Starting Smart Geo Inventory server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Reloading Smart Geo Inventory server...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"Smart Geo Inventory server ready. Listening on {bind}")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    print("Forked child, re-executing.")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"Worker received INT or QUIT signal (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    print(f"Worker received SIGABRT signal (pid: {worker.pid})")
