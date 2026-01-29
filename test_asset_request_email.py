"""
Test script untuk mengecek admin dan kirim test email untuk asset request
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User, AssetRequest
from app.services.notifications import notify_asset_request_created

app = create_app()

print("=" * 60)
print("  DIAGNOSA EMAIL ASSET REQUEST")
print("=" * 60)

with app.app_context():
    # Cek semua admin
    print("\n[CEK 1] Daftar Admin Users:")
    print("-" * 60)
    admins = User.query.filter_by(role='admin').all()

    if not admins:
        print("[WARNING] Tidak ada admin user sama sekali!")
    else:
        for i, admin in enumerate(admins, 1):
            print(f"\nAdmin #{i}:")
            print(f"  ID: {admin.id}")
            print(f"  Name: {admin.name}")
            print(f"  Email: {admin.email}")
            print(f"  Is Active: {admin.is_active}")
            print(f"  Email Notifications: {admin.email_notifications}")
            print(f"  Should Receive: {admin.should_receive_email_notifications()}")

    # Filter admin yang aktif dan mau notifikasi
    active_admins = [admin for admin in admins if admin.should_receive_email_notifications()]

    print(f"\n[CEK 2] Admin yang akan menerima email: {len(active_admins)}")
    if not active_admins:
        print("[WARNING] Tidak ada admin yang akan menerima email!")
        print("\nSolusi:")
        print("1. Pastikan admin punya email yang valid")
        print("2. Pastikan admin is_active = True")
        print("3. Pastikan admin email_notifications = True")
    else:
        for admin in active_admins:
            print(f"  - {admin.name} ({admin.email})")

    # Cek asset request terakhir
    print("\n[CEK 3] Asset Request Terakhir:")
    print("-" * 60)
    last_request = AssetRequest.query.order_by(AssetRequest.created_at.desc()).first()

    if last_request:
        print(f"ID: {last_request.id}")
        print(f"Unit: {last_request.unit.name if last_request.unit else 'N/A'}")
        print(f"Requester: {last_request.requester.name if last_request.requester else 'N/A'}")
        print(f"Status: {last_request.status}")
        print(f"Created: {last_request.created_at}")

        # Test kirim email
        print("\n[TEST] Mencoba kirim email ke admin...")
        print("-" * 60)
        result = notify_asset_request_created(last_request)
        if result:
            print("[SUCCESS] Email berhasil dikirim!")
        else:
            print("[FAILED] Gagal kirim email. Cek log aplikasi untuk detail error.")
    else:
        print("[INFO] Tidak ada asset request di database")

print("\n" + "=" * 60)
