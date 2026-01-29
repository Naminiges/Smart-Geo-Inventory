"""
Script untuk menguji pengiriman email dengan config SSL
Run dengan: python test_email.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom mail helper
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.utils.mail_helper import SSLMail
from flask_mail import Message
from flask import Flask

# Create Flask app untuk testing
app = Flask(__name__)

# Konfigurasi Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 587)
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
app.config['MAIL_TIMEOUT'] = 30  # 30 seconds timeout

mail = SSLMail()
mail.init_app(app)

def test_send_email():
    """Test kirim email sederhana"""

    # Cek konfigurasi
    print("=" * 50)
    print("KONFIGURASI EMAIL")
    print("=" * 50)
    print(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
    print(f"MAIL_PORT: {app.config['MAIL_PORT']}")
    print(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
    print(f"MAIL_USE_SSL: {app.config['MAIL_USE_SSL']}")
    print(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
    print(f"MAIL_PASSWORD: {'***' if app.config['MAIL_PASSWORD'] else 'NOT SET'}")
    print(f"MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")
    print("=" * 50)

    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        print("\n[ERROR] MAIL_USERNAME atau MAIL_PASSWORD belum di set!")
        print("Silakan cek file .env Anda")
        return False

    # Gunakan MAIL_USERNAME sebagai email tujuan (test sendiri)
    to_email = app.config['MAIL_USERNAME']
    print(f"\n[INFO] Mengirim email test ke: {to_email}")
    print("[INFO] Mohon tunggu...\n")

    with app.app_context():
        try:
            # Buat email test sederhana
            msg = Message(
                subject='[TEST] Email dari Smart Geo Inventory (Flask-Mail SSL)',
                recipients=[to_email],
                html="""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #28a745;">Test Email Berhasil!</h2>
                        <p>Ini adalah email test dari aplikasi <strong>Smart Geo Inventory</strong>.</p>
                        <p>Email dikirim menggunakan <strong>Flask-Mail dengan custom SSLMail</strong>.</p>
                        <p style="color: #6c757d;">
                            Konfigurasi: SSL (port 465)
                        </p>
                        <hr>
                        <p style="color: #7f8c8d; font-size: 12px;">
                            Email ini dikirim secara otomatis, jangan dibalas.
                        </p>
                    </div>
                </body>
                </html>
                """
            )

            # Kirim email
            mail.send(msg)

            print("[SUCCESS] Email berhasil dikirim!")
            print(f"[INFO] Silakan cek inbox (dan spam folder) di: {to_email}")
            return True

        except Exception as e:
            print(f"[ERROR] Gagal mengirim email: {str(e)}")
            print("\n[INFO] Tips troubleshooting:")
            print("1. Pastikan MAIL_USERNAME dan MAIL_PASSWORD sudah benar")
            print("2. Untuk Gmail, gunakan App Password (bukan password biasa)")
            print("   - Buat App Password: https://myaccount.google.com/apppasswords")
            print("3. Pastikan 'Less secure app access' sudah diaktifkan (jika menggunakan password biasa)")
            print("4. Cek koneksi internet")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  TEST EMAIL - SMART GEO INVENTORY")
    print("=" * 50 + "\n")

    result = test_send_email()

    print("\n" + "=" * 50)
    if result:
        print("  TEST SELESAI - BERHASIL")
    else:
        print("  TEST SELESAI - GAGAL")
    print("=" * 50 + "\n")

    sys.exit(0 if result else 1)
