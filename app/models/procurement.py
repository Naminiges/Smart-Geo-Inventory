from datetime import datetime
from app import db
from app.models.base import BaseModel


class Procurement(BaseModel):
    """Procurement model for tracking purchase requests and orders"""
    __tablename__ = 'procurements'

    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected, received, completed

    # Request tracking
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Approval tracking
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)

    # Rejection tracking
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejection_date = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Goods receipt tracking
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    receipt_date = db.Column(db.DateTime)
    receipt_number = db.Column(db.String(100))  # Nomor tanda terima
    actual_quantity = db.Column(db.Integer)  # Total jumlah yang diterima (akumulatif)

    # Serial numbers storage (JSON array)
    # Format: ["SN001", "SN002", "SN003"]
    serial_numbers = db.Column(db.Text)  # Store as JSON string

    # Receipt history (JSON array of receipts for partial receiving)
    # Format: [{"receipt_number": "INV-001", "quantity": 2, "serials": ["SN1", "SN2"], "date": "2024-01-01", "received_by": 1}, ...]
    receipt_history = db.Column(db.Text)  # Store as JSON string

    # Temporary new item data (if item doesn't exist)
    new_item_name = db.Column(db.String(200))
    new_item_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    new_item_unit = db.Column(db.String(50))

    # Completion tracking
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    completion_date = db.Column(db.DateTime)

    # Notes
    request_notes = db.Column(db.Text)  # Alasan permohonan
    notes = db.Column(db.Text)  # Catatan tambahan

    # Relationships
    supplier = db.relationship('Supplier', backref='procurements')
    item = db.relationship('Item', backref='procurements')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_procurements')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_procurements')
    rejecter = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_procurements')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='received_procurements')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_procurements')

    @property
    def total_price(self):
        """Calculate total price"""
        if self.unit_price:
            return self.quantity * self.unit_price
        return 0

    @property
    def total_received(self):
        """Get total quantity received so far"""
        return self.actual_quantity if self.actual_quantity else 0

    @property
    def remaining_quantity(self):
        """Get remaining quantity to receive"""
        return self.quantity - self.total_received

    @property
    def is_fully_received(self):
        """Check if all requested items have been received"""
        return self.total_received >= self.quantity

    @property
    def can_be_completed(self):
        """Check if procurement can be completed"""
        return self.status == 'received' and self.is_fully_received

    def get_receipt_history(self):
        """Get receipt history as list"""
        import json
        if self.receipt_history:
            return json.loads(self.receipt_history)
        return []

    def add_receipt_to_history(self, quantity_received, serial_numbers_list, user_id):
        """Add a delivery update to the history (single invoice, multiple deliveries)"""
        import json

        # Get existing history
        history = self.get_receipt_history()

        # Check for duplicate serial numbers within this procurement
        existing_serials = json.loads(self.serial_numbers) if self.serial_numbers else []
        duplicates = []
        for sn in serial_numbers_list:
            if sn in existing_serials:
                duplicates.append(sn)

        if duplicates:
            return False, f'Serial number sudah terdaftar di pengiriman sebelumnya: {", ".join(duplicates[:5])}{"..." if len(duplicates) > 5 else ""}'

        # Add new delivery record
        new_delivery = {
            'date': datetime.utcnow().isoformat(),
            'quantity': quantity_received,
            'serials': serial_numbers_list,
            'received_by': user_id,
            'cumulative_total': (self.actual_quantity or 0) + quantity_received
        }
        history.append(new_delivery)

        # Save history
        self.receipt_history = json.dumps(history)

        # Update actual_quantity (akumulatif)
        self.actual_quantity = (self.actual_quantity or 0) + quantity_received

        # Update serial_numbers (merge existing with new)
        all_serials = existing_serials + serial_numbers_list
        self.serial_numbers = json.dumps(all_serials)

        self.save()
        return True, f'Penerimaan berhasil dicatat. Total: {self.actual_quantity} unit.'

    def approve(self, user_id, supplier_id=None):
        """Approve procurement request"""
        if self.status != 'pending':
            return False, 'Hanya pengadaan dengan status pending yang bisa disetujui'

        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.utcnow()
        if supplier_id:
            self.supplier_id = supplier_id
        self.save()
        return True, 'Pengadaan berhasil disetujui'

    def reject(self, user_id, reason=None):
        """Reject procurement request"""
        if self.status != 'pending':
            return False, 'Hanya pengadaan dengan status pending yang bisa ditolak'

        self.status = 'rejected'
        self.rejected_by = user_id
        self.rejection_date = datetime.utcnow()
        self.rejection_reason = reason
        self.save()
        return True, 'Pengadaan berhasil ditolak'

    def receive_goods(self, user_id, receipt_number, quantity_received=None, serial_numbers=None):
        """Record goods receipt - supports partial receiving with single invoice"""
        if self.status != 'approved' and self.status != 'received':
            return False, 'Hanya pengadaan yang sudah disetujui yang bisa menerima barang'

        import json

        # Parse serial numbers - handle both string and list input
        serial_numbers_list = []
        if serial_numbers:
            if isinstance(serial_numbers, list):
                # Already a list (from view)
                serial_numbers_list = serial_numbers
            elif isinstance(serial_numbers, str):
                # String input (backward compatibility)
                serial_numbers_list = [sn.strip() for sn in serial_numbers.split('\n') if sn.strip()]
            else:
                # Try to convert to list
                serial_numbers_list = list(serial_numbers)

        # Validate quantity matches serial numbers count
        if quantity_received and len(serial_numbers_list) != quantity_received:
            return False, f'Jumlah serial number ({len(serial_numbers_list)}) harus sama dengan jumlah barang ({quantity_received})'

        # If this is the first receipt, set invoice number and update status
        if self.status == 'approved':
            self.status = 'received'
            self.received_by = user_id
            self.receipt_number = receipt_number  # Set invoice number on first receive
            self.receipt_date = datetime.utcnow()

        # For subsequent receives, ensure invoice number matches
        if self.receipt_number and self.receipt_number != receipt_number:
            return False, f'Nomor invoice harus sama dengan yang sudah terdaftar ({self.receipt_number}). Gunakan invoice yang sama.'

        # Validate: tidak boleh melebihi quantity yang diminta
        if self.total_received + quantity_received > self.quantity:
            return False, f'Total barang yang diterima ({self.total_received + quantity_received}) tidak boleh melebihi jumlah yang diminta ({self.quantity})'

        # Add to receipt history (tracking each delivery with date)
        success, message = self.add_receipt_to_history(quantity_received, serial_numbers_list, user_id)

        if success:
            if self.is_fully_received:
                return True, f'Barang berhasil diterima. Semua barang ({self.actual_quantity}/{self.quantity}) sudah lengkap! Siap untuk diselesaikan.'
            else:
                return True, f'Barang berhasil diterima. Total terima: {self.actual_quantity}/{self.quantity} unit. Masih kurang {self.remaining_quantity} unit.'
        else:
            return False, message

    def complete(self, user_id, warehouse_id=1):
        """Mark procurement as completed and add stock with item details"""
        from app.models.inventory import Stock, StockTransaction
        from app.models.master_data import ItemDetail
        import json

        # Validasi: harus status received dan semua barang sudah diterima
        if not self.is_fully_received:
            return False, f'Pengadaan belum bisa diselesaikan. Barang yang diterima baru {self.total_received}/{self.quantity} unit. Masih kurang {self.remaining_quantity} unit.'

        if not self.item_id:
            return False, 'Item harus diisi sebelum menyelesaikan pengadaan'

        try:
            # Get serial numbers
            serial_numbers = json.loads(self.serial_numbers) if self.serial_numbers else []

            # Create ItemDetail for each serial number (skip if already exists)
            items_created = 0
            items_skipped = 0
            for serial_number in serial_numbers:
                # Check if ItemDetail already exists for this serial number
                existing_detail = ItemDetail.query.filter_by(serial_number=serial_number).first()

                if existing_detail:
                    # Skip if already exists
                    items_skipped += 1
                    continue

                # Create new ItemDetail
                item_detail = ItemDetail(
                    item_id=self.item_id,
                    serial_number=serial_number,
                    status='available',
                    supplier_id=self.supplier_id,
                    warehouse_id=warehouse_id,
                    specification_notes=f'Diterima melalui pengadaan #{self.id}'
                )
                item_detail.save()
                items_created += 1

            # Add to stock
            stock = Stock.query.filter_by(
                item_id=self.item_id,
                warehouse_id=warehouse_id
            ).first()

            if not stock:
                stock = Stock(item_id=self.item_id, warehouse_id=warehouse_id, quantity=0)
                stock.save()

            # Use actual_quantity (total received)
            quantity_to_add = self.actual_quantity if self.actual_quantity else self.quantity
            stock.add_stock(quantity_to_add)

            # Log transaction
            transaction = StockTransaction(
                item_id=self.item_id,
                warehouse_id=warehouse_id,
                transaction_type='IN',
                quantity=quantity_to_add,
                note=f'Pengadaan #{self.id} - {self.total_received} unit'
            )
            transaction.save()

            # Update procurement status
            self.status = 'completed'
            self.completed_by = user_id
            self.completion_date = datetime.utcnow()
            self.save()

            # Build success message
            message_parts = []
            message_parts.append(f'{items_created} unit baru ditambahkan ke stok')
            if items_skipped > 0:
                message_parts.append(f'{items_skipped} unit sudah ada sebelumnya (dilewati)')

            return True, f'Pengadaan berhasil diselesaikan. {", ".join(message_parts)}.'
        except Exception as e:
            return False, f'Error menyelesaikan pengadaan: {str(e)}'

    def __repr__(self):
        return f'<Procurement #{self.id} {self.item.name if self.item else "N/A"} Qty:{self.quantity}>'
