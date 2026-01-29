"""
Script untuk mendiagnosa masalah koneksi email
"""
import socket
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.environ.get('MAIL_USERNAME')
MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)

print("=" * 60)
print("  DIAGNOSA KONEKSI SMTP - SMART GEO INVENTORY")
print("=" * 60)
print(f"Email: {EMAIL}")
print(f"Mail Server: {MAIL_SERVER}")
print(f"Mail Port: {MAIL_PORT}")
print("=" * 60)

# Test 1: DNS Resolution
print("\n[TEST 1] Cek DNS resolution untuk smtp.gmail.com...")
try:
    ip_address = socket.gethostbyname('smtp.gmail.com')
    print(f"[SUCCESS] smtp.gmail.com resolved ke: {ip_address}")
except socket.gaierror as e:
    print(f"[FAILED] Tidak bisa resolve DNS: {e}")
    print("\n[TIPS] Cek koneksi internet Anda")
    exit(1)

# Test 2: TCP Connection
print(f"\n[TEST 2] Cek koneksi TCP ke {MAIL_SERVER}:{MAIL_PORT}...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((MAIL_SERVER, MAIL_PORT))
    sock.close()

    if result == 0:
        print(f"[SUCCESS] Bisa terkoneksi ke {MAIL_SERVER}:{MAIL_PORT}")
    else:
        print(f"[FAILED] Tidak bisa terkoneksi (error code: {result})")
        print("\n[KEMUNGKINAN MASALAH]:")
        print("1. Firewall memblokir port 587")
        print("2. Jaringan kantor/universitas memblokir SMTP")
        print("3. Perlu proxy untuk koneksi internet")
        exit(1)
except socket.timeout:
    print(f"[FAILED] Connection timeout")
    print("\n[KEMUNGKINAN MASALAH]:")
    print("1. Koneksi internet lambat atau tidak stabil")
    print("2. Firewall memblokir koneksi")
    exit(1)
except Exception as e:
    print(f"[FAILED] Error: {e}")
    exit(1)

# Test 3: Port alternatif (465 untuk SSL)
print(f"\n[TEST 3] Cek port alternatif 465 (SSL)...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex(('smtp.gmail.com', 465))
    sock.close()

    if result == 0:
        print("[SUCCESS] Port 465 terbuka!")
        print("\n[SARAN] Coba gunakan port 465 dengan SSL:")
        print("  Di file .env, tambahkan:")
        print("  MAIL_PORT=465")
        print("  MAIL_USE_SSL=True")
        print("  MAIL_USE_TLS=False")
    else:
        print("[FAILED] Port 465 juga tidak bisa diakses")
        print("\n[KEMUNGKINAN MASALAH]:")
        print("Jaringan Anda memblokir semua koneksi SMTP keluar")
except Exception as e:
    print(f"[INFO] Error saat cek port 465: {e}")

print("\n" + "=" * 60)
print("  DIAGNOSA SELESAI")
print("=" * 60)
