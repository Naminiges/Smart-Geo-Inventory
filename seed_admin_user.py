#!/usr/bin/env python3
"""
Script untuk membuat user admin di database Smart Geo Inventory
Penggunaan:
    python3 seed_admin_user.py
"""

import sys
import os

# Tambahkan root project ke path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User


def create_admin_user():
    """Membuat user admin jika belum ada"""

    # Data admin default
    admin_data = {
        'name': 'Administrator',
        'email': 'admin@smartgeo.com',
        'password': 'admin123',  # GANTI PASSWORD INI setelah login pertama!
        'role': 'admin',
        'is_active': True,
        'phone': '6281234567890',  # Optional: untuk WhatsApp notifications
        'email_notifications': True
    }

    print("=" * 60)
    print("SEED ADMIN USER - SMART GEO INVENTORY")
    print("=" * 60)

    # Cek apakah user admin sudah ada
    existing_admin = User.query.filter_by(email=admin_data['email']).first()

    if existing_admin:
        print(f"\n⚠️  User admin dengan email '{admin_data['email']}' sudah ada!")
        print(f"   Nama: {existing_admin.name}")
        print(f"   Role: {existing_admin.role}")
        print(f"   Active: {existing_admin.is_active}")

        # Tanyakan apakah ingin update password
        try:
            response = input("\nApakah ingin update password? (y/n): ").lower()
            if response == 'y':
                new_password = input("Masukkan password baru: ")
                existing_admin.set_password(new_password)
                db.session.commit()
                print("✅ Password berhasil diupdate!")
            else:
                print("❌ Tidak ada perubahan.")
        except EOFError:
            # Jika running di non-interactive environment
            print("❌ Tidak ada perubahan (non-interactive mode).")

        return

    # Buat user admin baru
    print(f"\n📝 Membuat user admin baru...")
    print(f"   Nama: {admin_data['name']}")
    print(f"   Email: {admin_data['email']}")
    print(f"   Password: {admin_data['password']}")
    print(f"   Role: {admin_data['role']}")

    try:
        admin_user = User(
            name=admin_data['name'],
            email=admin_data['email'],
            role=admin_data['role'],
            is_active=admin_data['is_active'],
            phone=admin_data['phone'],
            email_notifications=admin_data['email_notifications']
        )
        admin_user.set_password(admin_data['password'])

        db.session.add(admin_user)
        db.session.commit()

        print("\n✅ User admin berhasil dibuat!")
        print(f"   ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Role: {admin_user.role}")
        print(f"   Active: {admin_user.is_active}")

        print("\n" + "=" * 60)
        print("⚠️  PENTING: GANTI PASSWORD SETELAH LOGIN PERTAMA!")
        print("=" * 60)
        print("\nLogin credentials:")
        print(f"   Email:    {admin_data['email']}")
        print(f"   Password: {admin_data['password']}")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main function"""
    # Create app context
    app = create_app()

    with app.app_context():
        create_admin_user()


if __name__ == '__main__':
    main()
