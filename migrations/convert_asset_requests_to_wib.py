"""
Migration: Convert asset request timestamps from UTC to WIB (GMT+7)
This adds 7 hours to existing timestamps to convert them to WIB
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from datetime import timedelta

def migrate():
    """Execute the migration"""
    app = create_app()

    with app.app_context():
        print("Starting migration: Convert asset_requests timestamps to WIB...")

        # Get all asset requests
        from app.models.asset_request import AssetRequest
        asset_requests = AssetRequest.query.all()

        print(f"\nFound {len(asset_requests)} asset requests to convert")

        converted_count = 0
        for ar in asset_requests:
            updated = False

            # Convert request_date (add 7 hours if not None)
            if ar.request_date:
                old_date = ar.request_date
                ar.request_date = ar.request_date + timedelta(hours=7)
                print(f"  Request #{ar.id}: request_date {old_date} -> {ar.request_date}")
                updated = True

            # Convert verified_at (add 7 hours if not None)
            if ar.verified_at:
                old_date = ar.verified_at
                ar.verified_at = ar.verified_at + timedelta(hours=7)
                print(f"  Request #{ar.id}: verified_at {old_date} -> {ar.verified_at}")
                updated = True

            # Convert distributed_at (add 7 hours if not None)
            if ar.distributed_at:
                old_date = ar.distributed_at
                ar.distributed_at = ar.distributed_at + timedelta(hours=7)
                print(f"  Request #{ar.id}: distributed_at {old_date} -> {ar.distributed_at}")
                updated = True

            # Convert received_at (add 7 hours if not None)
            if ar.received_at:
                old_date = ar.received_at
                ar.received_at = ar.received_at + timedelta(hours=7)
                print(f"  Request #{ar.id}: received_at {old_date} -> {ar.received_at}")
                updated = True

            if updated:
                converted_count += 1

        # Save all changes
        db.session.commit()

        print(f"\n✓ Migration completed successfully!")
        print(f"Converted {converted_count} asset request timestamps to WIB (GMT+7)")
        print("\nAll timestamps have been converted from UTC to WIB by adding 7 hours.")


def rollback():
    """Rollback the migration (subtract 7 hours)"""
    app = create_app()

    with app.app_context():
        print("Starting rollback: Convert asset_requests timestamps back to UTC...")

        from app.models.asset_request import AssetRequest
        asset_requests = AssetRequest.query.all()

        print(f"\nFound {len(asset_requests)} asset requests to rollback")

        converted_count = 0
        for ar in asset_requests:
            updated = False

            # Rollback request_date (subtract 7 hours if not None)
            if ar.request_date:
                old_date = ar.request_date
                ar.request_date = ar.request_date - timedelta(hours=7)
                print(f"  Request #{ar.id}: request_date {old_date} -> {ar.request_date}")
                updated = True

            # Rollback verified_at (subtract 7 hours if not None)
            if ar.verified_at:
                old_date = ar.verified_at
                ar.verified_at = ar.verified_at - timedelta(hours=7)
                print(f"  Request #{ar.id}: verified_at {old_date} -> {ar.verified_at}")
                updated = True

            # Rollback distributed_at (subtract 7 hours if not None)
            if ar.distributed_at:
                old_date = ar.distributed_at
                ar.distributed_at = ar.distributed_at - timedelta(hours=7)
                print(f"  Request #{ar.id}: distributed_at {old_date} -> {ar.distributed_at}")
                updated = True

            # Rollback received_at (subtract 7 hours if not None)
            if ar.received_at:
                old_date = ar.received_at
                ar.received_at = ar.received_at - timedelta(hours=7)
                print(f"  Request #{ar.id}: received_at {old_date} -> {ar.received_at}")
                updated = True

            if updated:
                converted_count += 1

        # Save all changes
        db.session.commit()

        print(f"\n✓ Rollback completed!")
        print(f"Rolled back {converted_count} asset request timestamps to UTC")
        print("\nAll timestamps have been converted back from WIB to UTC by subtracting 7 hours.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration for converting timestamps to WIB')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
