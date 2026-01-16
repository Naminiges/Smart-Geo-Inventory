import os
from app import create_app, db
from app.models import User, Warehouse, Category, Item

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Warehouse': Warehouse,
        'Category': Category,
        'Item': Item
    }


@app.cli.command()
def init_db():
    """Initialize the database with sample data"""
    from app.models import User, Warehouse, Category, Item, Supplier

    print("Creating database tables...")
    db.create_all()

    # Check if data already exists
    if User.query.first():
        print("Database already initialized!")
        return

    print("Creating sample data...")

    # Create admin user
    admin = User(
        name='Admin User',
        email='admin@smartgeo.com',
        role='admin'
    )
    admin.set_password('admin123')
    admin.save()

    # Create warehouse staff
    warehouse = Warehouse(
        name='Gudang Pusat',
        address='Universitas Sumatera Utara, Padang Bulan, Medan'
    )
    warehouse.set_coordinates(3.561676, 98.6563423)
    warehouse.save()

    warehouse_staff = User(
        name='Warehouse Staff',
        email='warehouse@smartgeo.com',
        role='warehouse_staff',
        warehouse_id=warehouse.id
    )
    warehouse_staff.set_password('warehouse123')
    warehouse_staff.save()

    # Create field staff
    field_staff = User(
        name='Field Staff',
        email='field@smartgeo.com',
        role='field_staff'
    )
    field_staff.set_password('field123')
    field_staff.save()

    # Create categories
    category1 = Category(
        name='Networking',
        description='Perangkat jaringan'
    )
    category1.save()

    category2 = Category(
        name='Computer',
        description='Perangkat komputer'
    )
    category2.save()

    # Create items
    item1 = Item(
        name='Router Cisco',
        item_code='NET-001',
        unit='unit',
        category_id=category1.id
    )
    item1.save()

    item2 = Item(
        name='Switch TP-Link',
        item_code='NET-002',
        unit='unit',
        category_id=category1.id
    )
    item2.save()

    # Create supplier
    supplier = Supplier(
        name='PT Teknologi Indonesia',
        contact_person='Budi Santoso',
        phone='08123456789',
        email='sales@teknologi.co.id',
        address='Jl. Teknologi No. 123, Jakarta'
    )
    supplier.save()

    print("Database initialized successfully!")
    print("Login credentials:")
    print("Admin: admin@smartgeo.com / admin123")
    print("Warehouse Staff: warehouse@smartgeo.com / warehouse123")
    print("Field Staff: field@smartgeo.com / field123")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
