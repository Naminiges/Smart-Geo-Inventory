"""
Script untuk test koneksi SMTP sederhana
"""
import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

EMAIL = os.environ.get('MAIL_USERNAME')
PASSWORD = os.environ.get('MAIL_PASSWORD')

print("=" * 50)
print("TEST KONEKSI SMTP GMAIL")
print("=" * 50)
print(f"Email: {EMAIL}")
print(f"Password: {'***SET***' if PASSWORD else 'NOT SET'}")
print("=" * 50)

if not EMAIL or not PASSWORD:
    print("\n[ERROR] EMAIL atau PASSWORD belum di set di .env")
    exit(1)

print("\n[INFO] Mencoba koneksi ke smtp.gmail.com:587...")
print("[INFO] Mohon tunggu...\n")

try:
    # Connect ke SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
    print("[SUCCESS] Terkoneksi ke smtp.gmail.com")

    # Start TLS
    server.starttls()
    print("[SUCCESS] TLS diaktifkan")

    # Login
    server.login(EMAIL, PASSWORD)
    print("[SUCCESS] Login berhasil")

    # Buat email
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = '[TEST] Email dari Smart Geo Inventory'

    body = """
    <html>
    <body>
        <h2>Test Email Berhasil!</h2>
        <p>Ini adalah email test dari aplikasi <strong>Smart Geo Inventory</strong>.</p>
        <p>Jika Anda menerima email ini, konfigurasi email sudah benar.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(body, 'html'))

    # Kirim email
    server.send_message(msg)
    print(f"[SUCCESS] Email berhasil dikirim ke {EMAIL}")

    # Disconnect
    server.quit()
    print("[SUCCESS] Disconnect dari server")

    print("\n" + "=" * 50)
    print("  TEST SELESAI - BERHASIL!")
    print(f"  Silakan cek inbox di {EMAIL}")
    print("=" * 50)

except smtplib.SMTPAuthenticationError as e:
    print(f"\n[ERROR] Authentication Error: {e}")
    print("\n[TIPS] Masalah yang mungkin terjadi:")
    print("1. Password salah - gunakan App Password, bukan password Gmail biasa")
    print("2. 2FA belum aktif - aktifkan 2FA terlebih dahulu")
    print("3. App Password belum dibuat - buat di: https://myaccount.google.com/apppasswords")
    exit(1)

except smtplib.SMTPException as e:
    print(f"\n[ERROR] SMTP Error: {e}")
    exit(1)

except Exception as e:
    print(f"\n[ERROR] Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
