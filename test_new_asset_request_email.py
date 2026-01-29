"""
Test untuk membuat asset request baru dan cek apakah email terkirim
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User, AssetRequest, AssetRequestItem, Item, Unit
from app.services.notifications import notify_asset_request_created
from datetime import datetime

app = create_app()

print("=" * 60)
print("  TEST BUAT ASSET REQUEST BARU + EMAIL")
print("=" * 60)

with app.app_context():
    # Get unit user
    unit_user = User.query.filter_by(role='unit_staff').first()

    if not unit_user:
        print("[ERROR] Tidak ada user unit_staff!")
        exit(1)

    print(f"\n[INFO] User Unit: {unit_user.name} ({unit_user.email})")

    # Get user's unit
    from app.models import UserUnit
    user_unit = UserUnit.query.filter_by(user_id=unit_user.id).first()

    if not user_unit:
        print("[ERROR] User tidak punya unit!")
        exit(1)

    print(f"[INFO] Unit: {user_unit.unit.name}")

    # Get an item
    item = Item.query.first()

    if not item:
        print("[ERROR] Tidak ada item di database!")
        exit(1)

    print(f"[INFO] Item: {item.name}")

    # Create asset request
    print("\n[STEP 1] Membuat asset request...")
    asset_request = AssetRequest(
        unit_id=user_unit.unit_id,
        requested_by=unit_user.id,
        request_date=datetime.now(),
        request_notes="Test email notifikasi",
        status='pending'
    )
    asset_request.save()
    print(f"[SUCCESS] Asset Request #{asset_request.id} dibuat!")

    # Create asset request item
    print("\n[STEP 2] Menambahkan item...")
    asset_request_item = AssetRequestItem(
        asset_request_id=asset_request.id,
        item_id=item.id,
        quantity=1,
        unit_detail_id=None,
        room_notes='Test'
    )
    asset_request_item.save()
    print("[SUCCESS] Item ditambahkan!")

    # Send email notification
    print("\n[STEP 3] Mengirim email ke admin...")
    print("-" * 60)

    result = notify_asset_request_created(asset_request)

    if result:
        print("\n[SUCCESS] Email berhasil dikirim ke admin!")
        print("[INFO] Silakan cek inbox admin (perrysiregar0@gmail.com)")
    else:
        print("\n[FAILED] Gagal mengirim email!")
        print("[INFO] Cek log Flask untuk detail error")

    # Cleanup (optional)
    print("\n[CLEANUP] Menghapus test data...")
    asset_request_item.delete()
    asset_request.delete()
    print("[SUCCESS] Test data dihapus")

print("\n" + "=" * 60)
print("  TEST SELESAI")
print("=" * 60)
