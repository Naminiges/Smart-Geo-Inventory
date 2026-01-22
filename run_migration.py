#!/usr/bin/env python
"""Run migration script"""
from app import create_app, db
from migrations.add_distribution_groups_table import upgrade

app = create_app()

with app.app_context():
    try:
        upgrade()
        print("Migration successful!")
        print("✓ Created distribution_groups table")
        print("✓ Added distribution_group_id to distributions table")
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
