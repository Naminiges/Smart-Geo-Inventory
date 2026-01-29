#!/usr/bin/env python3
"""
Debug script to check CSRF and Session configuration
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def debug_csrf_config():
    """Debug CSRF and session configuration"""
    app = create_app('production')

    print("=== CSRF and Session Configuration Debug ===\n")

    with app.app_context():
        # Check CSRF configuration
        print("CSRF Configuration:")
        print(f"  WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', 'Not set')}")
        print(f"  WTF_CSRF_TIME_LIMIT: {app.config.get('WTF_CSRF_TIME_LIMIT', 'Not set')}")
        print(f"  SECRET_KEY: {'Set' if app.config.get('SECRET_KEY') else 'Not set'}")
        print(f"  SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")

        # Check Session configuration
        print("\nSession Configuration:")
        print(f"  SESSION_TYPE: {app.config.get('SESSION_TYPE', 'Not set')}")
        print(f"  SESSION_FILE_DIR: {app.config.get('SESSION_FILE_DIR', 'Not set')}")
        print(f"  SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE', 'Not set')}")
        print(f"  SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY', 'Not set')}")
        print(f"  SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE', 'Not set')}")

        # Check if session directory exists
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir:
            print(f"\n  Session directory exists: {os.path.exists(session_dir)}")
            print(f"  Session directory is writable: {os.access(session_dir, os.W_OK) if os.path.exists(session_dir) else 'N/A'}")
            if os.path.exists(session_dir):
                print(f"  Session files count: {len([f for f in os.listdir(session_dir) if os.path.isfile(os.path.join(session_dir, f))])}")

        # Test CSRF token generation
        print("\nTesting CSRF Token Generation:")
        try:
            from flask_wtf.csrf import generate_csrf
            with app.test_request_context():
                csrf_token = generate_csrf()
                print(f"  CSRF Token generated: {csrf_token[:20]}..." if csrf_token else "Failed to generate")
                print(f"  CSRF Token length: {len(csrf_token)}")
        except Exception as e:
            print(f"  Error generating CSRF token: {str(e)}")

        # Test session
        print("\nTesting Session:")
        try:
            from flask import session
            with app.test_client() as client:
                # Make a request to login page
                response = client.get('/auth/login')
                print(f"  Login page status: {response.status_code}")

                # Check if session cookie is set
                cookies = [cookie for cookie in client.cookie_jar]
                print(f"  Cookies set: {len(cookies)}")
                for cookie in cookies:
                    print(f"    - {cookie.name}: {cookie.value[:20]}..." if cookie.value else f"    - {cookie.name}: (empty)")

                # Check if CSRF token is in the response
                if b'csrf_token' in response.data:
                    print(f"  CSRF token found in response: Yes")
                else:
                    print(f"  CSRF token found in response: No")

        except Exception as e:
            print(f"  Error testing session: {str(e)}")

        print("\n=== End of Debug ===")

if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    debug_csrf_config()
