#!/usr/bin/env python3
"""
Check environment configuration for Smart Geo Inventory
Run this script before starting the application
"""
import os
import sys
from dotenv import load_dotenv

print("=== Smart Geo Inventory Environment Check ===\n")

# Load environment variables
load_dotenv()

# Check required environment variables
required_vars = {
    'SECRET_KEY': 'Secret key for session encryption',
    'DATABASE_URL': 'PostgreSQL database connection string',
    'FLASK_ENV': 'Flask environment (development/production)',
    'MAIL_SERVER': 'SMTP server for email (optional)',
    'MAIL_USERNAME': 'SMTP username (optional)',
    'MAIL_PASSWORD': 'SMTP password (optional)',
}

optional_vars = {
    'REDIS_URL': 'Redis connection string (optional, for caching)',
}

print("Checking REQUIRED environment variables:")
all_ok = True
for var, desc in required_vars.items():
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if 'PASSWORD' in var or 'SECRET' in var:
            display_value = f"{value[:10]}..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  ✓ {var}: {display_value}")
        print(f"    Description: {desc}")
    else:
        print(f"  ✗ {var}: NOT SET")
        print(f"    Description: {desc}")
        all_ok = False

print("\nChecking OPTIONAL environment variables:")
for var, desc in optional_vars.items():
    value = os.environ.get(var)
    if value:
        display_value = value if 'PASSWORD' not in var else "***"
        print(f"  ✓ {var}: {display_value}")
        print(f"    Description: {desc}")
    else:
        print(f"  ○ {var}: Not set (optional)")
        print(f"    Description: {desc}")

# Check SECRET_KEY quality
print("\nChecking SECRET_KEY quality:")
secret_key = os.environ.get('SECRET_KEY')
if secret_key:
    if len(secret_key) < 20:
        print(f"  ⚠ WARNING: SECRET_KEY is too short ({len(secret_key)} chars). Recommended: 24+ chars")
        all_ok = False
    elif secret_key == 'dev-secret-key-change-in-production':
        print(f"  ⚠ WARNING: Using default SECRET_KEY. Change this in production!")
        all_ok = False
    else:
        print(f"  ✓ SECRET_KEY is properly configured ({len(secret_key)} chars)")
else:
    print(f"  ✗ SECRET_KEY is not set!")
    all_ok = False

# Check if .env file exists
print("\nChecking .env file:")
if os.path.exists('.env'):
    print(f"  ✓ .env file exists")
else:
    print(f"  ⚠ WARNING: .env file not found in current directory")

# Check Python version
print("\nPython version:")
print(f"  Python {sys.version}")

# Check if required packages are installed
print("\nChecking required packages:")
try:
    import flask
    print(f"  ✓ Flask {flask.__version__}")
except ImportError:
    print(f"  ✗ Flask NOT installed")
    all_ok = False

try:
    import flask_wtf
    print(f"  ✓ Flask-WTF {flask_wtf.__version__}")
except ImportError:
    print(f"  ✗ Flask-WTF NOT installed")
    all_ok = False

try:
    import flask_session
    print(f"  ✓ Flask-Session {flask_session.__version__}")
except ImportError:
    print(f"  ○ Flask-Session NOT installed (optional)")

try:
    import gunicorn
    print(f"  ✓ Gunicorn {gunicorn.__version__}")
except ImportError:
    print(f"  ✗ Gunicorn NOT installed")
    all_ok = False

print("\n" + "="*50)
if all_ok:
    print("✓ All critical checks passed!")
    print("\nYou can now start the application:")
    print("  export $(cat .env | xargs)")
    print("  gunicorn -c gunicorn.conf.py wsgi:app")
else:
    print("✗ Some checks failed. Please fix the issues above.")
    print("\nMake sure to:")
    print("  1. Create a .env file with proper configuration")
    print("  2. Set a strong SECRET_KEY (24+ characters)")
    print("  3. Install all required packages: pip install -r requirements.txt")
    sys.exit(1)
