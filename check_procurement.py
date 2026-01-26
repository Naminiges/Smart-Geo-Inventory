from app import create_app
from app.models import Procurement, Stock, ItemDetail, ProcurementItem, Item

app = create_app()
with app.app_context():
    # Get all procurements
    procurements = Procurement.query.all()
    print(f'Total Procurements: {len(procurements)}')

    for p in procurements:
        print(f'\nProcurement: {p.id}, Status: {p.status}')
        if p.items:
            for pi in p.items:
                item_name = pi.item.name if pi.item else "N/A"
                print(f'  Item: {item_name} (ID: {pi.item_id})')
                print(f'    Requested Qty: {pi.quantity}')
                print(f'    Actual Qty: {pi.actual_quantity}')
                print(f'    Serial Numbers: {pi.serial_numbers}')

    # Check stocks
    stocks = Stock.query.all()
    print(f'\n\nStocks count: {len(stocks)}')
    for s in stocks:
        item = Item.query.get(s.item_id)
        item_name = item.name if item else "N/A"
        print(f'  Stock: {item_name} (item_id={s.item_id}, warehouse_id={s.warehouse_id}, qty={s.quantity})')

    # Check item details
    item_details = ItemDetail.query.all()
    print(f'\n\nItemDetails count: {len(item_details)}')
    print('First 10 ItemDetails:')
    for id in item_details[:10]:
        item = Item.query.get(id.item_id)
        item_name = item.name if item else "N/A"
        print(f'  ItemDetail: {item_name} (id={id.id}, item_id={id.item_id}, serial={id.serial_number}, warehouse_id={id.warehouse_id}, status={id.status})')
