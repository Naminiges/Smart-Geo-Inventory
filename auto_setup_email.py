"""
Script otomatis untuk mendeteksi konfigurasi email yang cocok dengan jaringan
Jalankan ini setiap kali pindah jaringan untuk mengetahui konfigurasi yang tepat

Usage: python auto_setup_email.py
"""
import os
import smtplib
import socket
from dotenv import load_dotenv, set_key

load_dotenv()

EMAIL = os.environ.get('MAIL_USERNAME')
PASSWORD = os.environ.get('MAIL_PASSWORD')

print("=" * 60)
print("  AUTO DETECT KONFIGURASI EMAIL")
print("=" * 60)
print(f"Email: {EMAIL}")
print(f"Password: {'***SET***' if PASSWORD else 'NOT SET'}")
print("=" * 60)

if not EMAIL or not PASSWORD:
    print("\n[ERROR] EMAIL atau PASSWORD belum di set!")
    exit(1)

def test_connection(port, use_ssl=False, use_tls=False):
    """Test koneksi ke port tertentu"""
    try:
        if use_ssl:
            conn = smtplib.SMTP_SSL('smtp.gmail.com', port, timeout=10)
        else:
            conn = smtplib.SMTP('smtp.gmail.com', port, timeout=10)
            if use_tls:
                conn.starttls()

        conn.login(EMAIL, PASSWORD)
        conn.quit()
        return True
    except Exception as e:
        return False

# Test Mode 1: TLS Port 587
print("\n[TEST 1] Mencoba TLS (Port 587)...")
if test_connection(587, use_tls=True):
    print("[SUCCESS] Port 587 TLS berhasil!")
    print("\nGunakan konfigurasi:")
    print("  MAIL_PORT=587")
    print("  MAIL_USE_TLS=True")
    print("  MAIL_USE_SSL=False")

    # Update .env
    set_key('.env', 'MAIL_PORT', '587')
    set_key('.env', 'MAIL_USE_TLS', 'True')
    set_key('.env', 'MAIL_USE_SSL', 'False')
    print("\n[INFO] File .env sudah diupdate!")
    exit(0)
else:
    print("[FAILED] Port 587 tidak bisa digunakan")

# Test Mode 2: SSL Port 465
print("\n[TEST 2] Mencoba SSL (Port 465)...")
if test_connection(465, use_ssl=True):
    print("[SUCCESS] Port 465 SSL berhasil!")
    print("\nGunakan konfigurasi:")
    print("  MAIL_PORT=465")
    print("  MAIL_USE_TLS=False")
    print("  MAIL_USE_SSL=True")

    # Update .env
    set_key('.env', 'MAIL_PORT', '465')
    set_key('.env', 'MAIL_USE_TLS', 'False')
    set_key('.env', 'MAIL_USE_SSL', 'True')
    print("\n[INFO] File .env sudah diupdate!")
    exit(0)
else:
    print("[FAILED] Port 465 tidak bisa digunakan")

print("\n" + "=" * 60)
print("[ERROR] TIDAK BISA TERKONEKSI KE GMAIL SMTP")
print("=" * 60)
print("\nKemungkinan masalah:")
print("1. Koneksi internet tidak stabil")
print("2. Firewall memblokir semua port SMTP")
print("3. Email/Password salah")
print("4. App Password belum dibuat")
print("\nSolusi:")
print("- Coba gunakan jaringan lain (WiFi berbeda)")
print("- Pastikan App Password sudah benar")
print("- Cek https://myaccount.google.com/apppasswords")
print("=" * 60)
exit(1)
