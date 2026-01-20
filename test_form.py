#!/usr/bin/env python
"""Test form validation"""
from app import create_app
from app.forms import AssetVerificationForm
from app.models import Warehouse

app = create_app()

with app.app_context():
    # Get warehouses
    warehouses = Warehouse.query.all()
    print(f"Found {len(warehouses)} warehouses")
    for w in warehouses:
        print(f"  - {w.id}: {w.name}")

    # Create form and set choices
    form = AssetVerificationForm()
    form.warehouse_id.choices = [('0', '-- Pilih Warehouse --')] + [(str(w.id), w.name) for w in warehouses]

    print(f"\nForm choices set:")
    print(form.warehouse_id.choices)

    # Simulate POST data
    from werkzeug.datastructures import MultiDict
    formdata = MultiDict([
        ('warehouse_id', '1'),
        ('csrf_token', 'test'),
        ('notes', 'Test verification')
    ])

    print(f"\nSimulating POST with warehouse_id=1")
    print(f"Form data: {dict(formdata)}")

    # Create form with POST data
    form2 = AssetVerificationForm(formdata)
    form2.warehouse_id.choices = [('0', '-- Pilih Warehouse --')] + [(str(w.id), w.name) for w in warehouses]

    print(f"\nForm validation result: {form2.validate()}")
    print(f"Warehouse ID value: {form2.warehouse_id.data} (type: {type(form2.warehouse_id.data)})")
    print(f"Form errors: {form2.errors}")

    if form2.validate():
        print("✅ Form validation PASSED")
    else:
        print("❌ Form validation FAILED")
        for field, errors in form2.errors.items():
            print(f"  {field}: {errors}")
