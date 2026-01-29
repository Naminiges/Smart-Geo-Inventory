"""
Script untuk test email dengan SSL (port 465)
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
print("TEST EMAIL DENGAN SSL (PORT 465)")
print("=" * 50)
print(f"Email: {EMAIL}")
print(f"Password: {'***SET***' if PASSWORD else 'NOT SET'}")
print("=" * 50)

if not EMAIL or not PASSWORD:
    print("\n[ERROR] EMAIL atau PASSWORD belum di set di .env")
    exit(1)

print("\n[INFO] Mencoba koneksi SSL ke smtp.gmail.com:465...")
print("[INFO] Mohon tunggu...\n")

try:
    # Connect dengan SSL langsung
    print("[1/4] Connecting to smtp.gmail.com:465 with SSL...")
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
    print("  [OK] Connected!")

    # Login
    print("[2/4] Logging in...")
    server.login(EMAIL, PASSWORD)
    print("  [OK] Login successful!")

    # Buat email
    print("[3/4] Creating email...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = '[TEST] Email dari Smart Geo Inventory (SSL)'

    body = """
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #28a745;">Test Email Berhasil! (SSL)</h2>
        <p>Ini adalah email test dari aplikasi <strong>Smart Geo Inventory</strong>.</p>
        <p>Email dikirim menggunakan <strong>SMTP_SSL (port 465)</strong>.</p>
        <p style="color: #6c757d;">Jika Anda menerima email ini, konfigurasi email sudah benar.</p>
        <hr>
        <p style="font-size: 12px; color: #adb5bd;">Email ini dikirim secara otomatis, jangan dibalas.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(body, 'html'))

    # Kirim email
    print("[4/4] Sending email...")
    server.send_message(msg)
    print(f"  [OK] Email sent to {EMAIL}!")

    # Disconnect
    server.quit()
    print("  [OK] Disconnected")

    print("\n" + "=" * 50)
    print("  TEST SELESAI - BERHASIL!")
    print(f"  Silakan cek inbox di {EMAIL}")
    print("=" * 50)
    print("\n[KONFIGURASI]")
    print("Update file .env Anda:")
    print("  MAIL_PORT=465")
    print("  MAIL_USE_TLS=False")
    print("  MAIL_USE_SSL=True")
    print("=" * 50)

except smtplib.SMTPAuthenticationError as e:
    print(f"\n[ERROR] Authentication Error: {e}")
    print("\n[TIPS] Masalah yang mungkin terjadi:")
    print("1. Password salah - gunakan App Password, bukan password Gmail biasa")
    print("2. 2FA belum aktif - aktifkan 2FA terlebih dahulu di Google Account")
    print("3. App Password belum dibuat - buat di: https://myaccount.google.com/apppasswords")
    print("\n[Cara buat App Password]:")
    print("  1. Buka https://myaccount.google.com/security")
    print("  2. Aktifkan 2-Step Verification")
    print("  3. Klik 'App passwords'")
    print("  4. Pilih 'Mail' dan device Anda")
    print("  5. Copy password yang diberikan")
    exit(1)

except smtplib.SMTPException as e:
    print(f"\n[ERROR] SMTP Error: {e}")
    print("\nCoba cek:")
    print("1. Koneksi internet aktif")
    print("2. App Password sudah benar")
    exit(1)

except Exception as e:
    print(f"\n[ERROR] Unexpected error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
