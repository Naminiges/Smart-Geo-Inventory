from datetime import datetime
from app import db
from app.models.base import BaseModel


class UnitProcurementItem(BaseModel):
    """Individual item within a unit procurement request"""
    __tablename__ = 'unit_procurement_items'

    unit_procurement_id = db.Column(db.Integer, db.ForeignKey('unit_procurements.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)

    # Temporary new item data (if item doesn't exist)
    new_item_name = db.Column(db.String(200))
    new_item_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    new_item_unit = db.Column(db.String(50))

    # Track the linked procurement item after admin approval
    linked_procurement_item_id = db.Column(db.Integer, db.ForeignKey('procurement_items.id'), nullable=True)

    # Relationships
    unit_procurement = db.relationship('UnitProcurement', backref='items')
    item = db.relationship('Item', backref='unit_procurement_items')
    linked_procurement_item = db.relationship('ProcurementItem', backref='unit_procurement_items')

    def __repr__(self):
        return f'<UnitProcurementItem #{self.id} {self.item.name if self.item else "N/A"} Qty:{self.quantity}>'


class UnitProcurement(BaseModel):
    """Procurement request model for Units - similar to warehouse procurement"""
    __tablename__ = 'unit_procurements'

    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    status = db.Column(db.String(20), default='pending_verification', nullable=False)
    # Status: pending_verification, verified, approved, rejected, in_procurement, received, completed, cancelled

    # Request tracking
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Admin verification tracking
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verification_date = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)

    # Approval tracking
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)

    # Rejection tracking
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejection_date = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Link to warehouse procurement created after admin approval
    procurement_id = db.Column(db.Integer, db.ForeignKey('procurements.id'), nullable=True)

    # Receipt tracking (for tracking when unit receives the items)
    unit_received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    unit_receipt_date = db.Column(db.DateTime)

    # Notes
    request_notes = db.Column(db.Text)  # Alasan permohonan
    admin_notes = db.Column(db.Text)  # Catatan admin

    # Relationships
    unit = db.relationship('Unit', backref='procurement_requests')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='unit_procurement_requests')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_unit_procurements')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_unit_procurements')
    rejecter = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_unit_procurements')
    procurement = db.relationship('Procurement', backref='unit_request')
    unit_receiver = db.relationship('User', foreign_keys=[unit_received_by], backref='received_unit_procurements')

    @property
    def total_quantity(self):
        """Get total quantity of all items in this procurement"""
        return sum(item.quantity for item in self.items) if self.items else 0

    @property
    def is_verified(self):
        """Check if request has been verified by admin"""
        return self.status not in ['pending_verification']

    @property
    def has_procurement(self):
        """Check if warehouse procurement has been created"""
        return self.procurement_id is not None

    def get_status_display(self):
        """Get human-readable status display"""
        status_map = {
            'pending_verification': 'Menunggu Verifikasi',
            'verified': 'Terverifikasi',
            'approved': 'Disetujui',
            'rejected': 'Ditolak',
            'in_procurement': 'Dalam Proses Pengadaan',
            'received': 'Barang Diterima',
            'completed': 'Selesai',
            'cancelled': 'Dibatalkan'
        }
        return status_map.get(self.status, self.status)

    def verify(self, user_id, notes=None):
        """Verify unit procurement request (admin action)"""
        if self.status != 'pending_verification':
            return False, 'Hanya permohonan dengan status pending_verification yang bisa diverifikasi'

        self.status = 'verified'
        self.verified_by = user_id
        self.verification_date = datetime.utcnow()
        self.verification_notes = notes
        self.save()
        return True, 'Permohonan berhasil diverifikasi'

    def approve(self, user_id):
        """Approve verified request and create warehouse procurement (admin action)"""
        if self.status != 'verified':
            return False, 'Hanya permohonan yang sudah diverifikasi yang bisa disetujui'

        # Create warehouse procurement
        from app.models.procurement import Procurement, ProcurementItem

        procurement = Procurement(
            requested_by=user_id,
            request_notes=f'Permohonan dari Unit: {self.unit.name}. {self.request_notes or ""}',
            notes=f'Unit Request ID: {self.id}. {self.admin_notes or ""}',
            status='pending'
        )
        procurement.save()

        # Copy items from unit procurement to warehouse procurement
        for unit_item in self.items:
            procurement_item = ProcurementItem(
                procurement_id=procurement.id,
                item_id=unit_item.item_id,
                quantity=unit_item.quantity,
                new_item_name=unit_item.new_item_name,
                new_item_category_id=unit_item.new_item_category_id,
                new_item_unit=unit_item.new_item_unit
            )
            procurement_item.save()

            # Link the unit procurement item to the warehouse procurement item
            unit_item.linked_procurement_item_id = procurement_item.id
            unit_item.save()

        # Update unit procurement status
        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.utcnow()
        self.procurement_id = procurement.id
        self.save()

        return True, f'Permohonan berhasil disetujui. Pengadaan #{procurement.id} telah dibuat di Warehouse'

    def reject(self, user_id, reason=None):
        """Reject unit procurement request (admin action)"""
        if self.status in ['completed', 'cancelled']:
            return False, 'Tidak bisa menolak permohonan yang sudah selesai atau dibatalkan'

        self.status = 'rejected'
        self.rejected_by = user_id
        self.rejection_date = datetime.utcnow()
        self.rejection_reason = reason
        self.save()
        return True, 'Permohonan berhasil ditolak'

    def update_status_from_procurement(self):
        """Update status based on linked warehouse procurement status"""
        if not self.procurement:
            return False, 'Tidak ada pengadaan yang terkait'

        procurement_status = self.procurement.status

        # Map warehouse procurement status to unit procurement status
        status_mapping = {
            'pending': 'in_procurement',
            'approved': 'in_procurement',
            'received': 'received',
            'completed': 'completed'
        }

        if procurement_status in status_mapping:
            self.status = status_mapping[procurement_status]
            self.save()

            # If completed, mark as received by unit
            if procurement_status == 'completed':
                self.unit_receipt_date = datetime.utcnow()

            return True, f'Status diperbarui: {self.status}'

        return False, 'Status pengadaan tidak dikenali'

    def cancel(self, user_id):
        """Cancel the unit procurement request"""
        if self.status in ['completed', 'in_procurement']:
            return False, 'Tidak bisa membatalkan permohonan yang sedang diproses atau sudah selesai'

        self.status = 'cancelled'
        self.save()
        return True, 'Permohonan berhasil dibatalkan'

    def __repr__(self):
        return f'<UnitProcurement #{self.id} Unit:{self.unit.name if self.unit else "N/A"} Status:{self.status}>'


class ProcurementItem(BaseModel):
    """Individual item within a procurement request"""
    __tablename__ = 'procurement_items'

    procurement_id = db.Column(db.Integer, db.ForeignKey('procurements.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)

    # Serial numbers storage (JSON array)
    # Format: ["SN001", "SN002", "SN003"]
    serial_numbers = db.Column(db.Text)  # Store as JSON string

    # Receipt tracking
    actual_quantity = db.Column(db.Integer, default=0)  # Total jumlah yang diterima (akumulatif)

    # Receipt history (JSON array of receipts for partial receiving)
    # Format: [{"receipt_number": "INV-001", "quantity": 2, "serials": ["SN1", "SN2"], "date": "2024-01-01", "received_by": 1}, ...]
    receipt_history = db.Column(db.Text)  # Store as JSON string

    # Temporary new item data (if item doesn't exist)
    new_item_name = db.Column(db.String(200))
    new_item_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    new_item_unit = db.Column(db.String(50))

    # Relationships
    procurement = db.relationship('Procurement', backref='items')
    item = db.relationship('Item', backref='procurement_items')

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

    def get_receipt_history(self):
        """Get receipt history as list"""
        import json
        if self.receipt_history:
            return json.loads(self.receipt_history)
        return []

    def add_receipt_to_history(self, quantity_received, serial_numbers_list, serial_units_list, user_id):
        """Add a delivery update to the history (single invoice, multiple deliveries)

        Args:
            quantity_received: Number of items received in this delivery
            serial_numbers_list: List of serial numbers (manual for networking, auto-generated for non-networking)
            serial_units_list: List of serial units (always auto-generated for ALL items)
            user_id: ID of user receiving the goods
        """
        import json
        from app.models.master_data import ItemDetail

        # Get existing history
        history = self.get_receipt_history()

        # Check for duplicate serial numbers within this procurement item
        existing_serials = json.loads(self.serial_numbers) if self.serial_numbers else []
        duplicates = []
        for sn in serial_numbers_list:
            if sn in existing_serials:
                duplicates.append(sn)

        if duplicates:
            return False, f'Serial number sudah terdaftar di pengiriman sebelumnya: {", ".join(duplicates[:5])}{"..." if len(duplicates) > 5 else ""}'

        # Create ItemDetail records immediately upon receipt
        # Get procurement object
        from app.models.procurement import Procurement
        procurement = Procurement.query.filter(
            Procurement.items.any(id=self.id)
        ).first()

        items_created = 0
        for i in range(quantity_received):
            serial_number = serial_numbers_list[i] if i < len(serial_numbers_list) else serial_units_list[i]
            serial_unit = serial_units_list[i] if i < len(serial_units_list) else serial_number

            # Check if ItemDetail with this serial_number already exists globally
            existing_detail = ItemDetail.query.filter_by(serial_number=serial_number).first()
            if existing_detail:
                continue

            # Check if ItemDetail with this serial_unit already exists globally
            existing_unit = ItemDetail.query.filter_by(serial_unit=serial_unit).first()
            if existing_unit:
                continue

            # Create new ItemDetail with status 'available' (in warehouse, not yet distributed)
            item_detail = ItemDetail(
                item_id=self.item_id,
                serial_number=serial_number,  # Manual for networking, auto-generated for non-networking
                serial_unit=serial_unit,  # Always auto-generated
                status='available',
                warehouse_id=None,  # Will be assigned when distributed/added to stock
                specification_notes=f'Diterima melalui procurement #{procurement.id if procurement else "N/A"}'
            )
            item_detail.save()
            items_created += 1

        # Add new delivery record
        new_delivery = {
            'date': datetime.utcnow().isoformat(),
            'quantity': quantity_received,
            'serials': serial_numbers_list,
            'serial_units': serial_units_list,
            'received_by': user_id,
            'cumulative_total': (self.actual_quantity or 0) + quantity_received,
            'item_details_created': items_created
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
        return True, f'Penerimaan berhasil dicatat. {items_created} ItemDetail dibuat. Total: {self.actual_quantity} unit.'

    def __repr__(self):
        return f'<ProcurementItem #{self.id} {self.item.name if self.item else "N/A"} Qty:{self.quantity}>'


class Procurement(BaseModel):
    """Procurement model for tracking purchase requests and orders"""
    __tablename__ = 'procurements'

    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)  # Warehouse tujuan
    # item_id and quantity removed - now using ProcurementItem for multiple items
    # item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    # quantity = db.Column(db.Integer, nullable=False)
    # unit_price = db.Column(db.Float, nullable=True)
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
    receipt_number = db.Column(db.String(100))  # Nomor tanda terima (now for the whole procurement)

    # Serial numbers storage - moved to ProcurementItem
    # serial_numbers = db.Column(db.Text)

    # Receipt history - moved to ProcurementItem
    # receipt_history = db.Column(db.Text)

    # Temporary new item data - moved to ProcurementItem
    # new_item_name = db.Column(db.String(200))
    # new_item_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    # new_item_unit = db.Column(db.String(50))

    # Completion tracking
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    completion_date = db.Column(db.DateTime)

    # Notes
    request_notes = db.Column(db.Text)  # Alasan permohonan
    notes = db.Column(db.Text)  # Catatan tambahan

    # Relationships
    warehouse = db.relationship('Warehouse', backref='procurements')
    # item = db.relationship('Item', backref='procurements') - removed, now using ProcurementItem
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_procurements')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_procurements')
    rejecter = db.relationship('User', foreign_keys=[rejected_by], backref='rejected_procurements')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='received_procurements')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_procurements')

    @property
    def procurement_code(self):
        """Generate procurement code like PC-000001"""
        return f"PC-{self.id:06d}"

    @property
    def created_by_user(self):
        """Get the user who created this procurement (alias for requester)"""
        return self.requester

    @property
    def total_quantity(self):
        """Get total quantity of all items in this procurement"""
        return sum(item.quantity for item in self.items) if self.items else 0

    @property
    def total_received(self):
        """Get total quantity received across all items"""
        return sum(item.total_received for item in self.items) if self.items else 0


    @property
    def remaining_quantity(self):
        """Get remaining quantity to receive across all items"""
        return sum(item.remaining_quantity for item in self.items) if self.items else 0

    @property
    def is_fully_received(self):
        """Check if all requested items have been received"""
        if not self.items:
            return False
        return all(item.is_fully_received for item in self.items)

    @property
    def can_be_completed(self):
        """Check if procurement can be completed"""
        return self.status == 'received' and self.is_fully_received

    def approve(self, user_id):
        """Approve procurement request"""
        if self.status != 'pending':
            return False, 'Hanya pengadaan dengan status pending yang bisa disetujui'

        self.status = 'approved'
        self.approved_by = user_id
        self.approval_date = datetime.utcnow()
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

    def receive_goods(self, user_id, receipt_number, items_data):
        """
        Record goods receipt for multiple items
        items_data format: [
            {
                'procurement_item_id': 1,
                'quantity_received': 5,
                'serial_numbers': ['SN1', 'SN2', ...],  # Manual for networking, auto-generated for non-networking
                'serial_units': ['SU-001', 'SU-002', ...]  # Always auto-generated
            },
            ...
        ]
        """
        if self.status != 'approved' and self.status != 'received':
            return False, 'Hanya pengadaan yang sudah disetujui yang bisa menerima barang'

        # If this is the first receipt, set invoice number and update status
        if self.status == 'approved':
            self.status = 'received'
            self.received_by = user_id
            self.receipt_number = receipt_number
            self.receipt_date = datetime.utcnow()

        # For subsequent receives, ensure invoice number matches
        if self.receipt_number and self.receipt_number != receipt_number:
            return False, f'Nomor invoice harus sama dengan yang sudah terdaftar ({self.receipt_number}). Gunakan invoice yang sama.'

        # Process each item
        results = []
        all_success = True
        for item_data in items_data:
            procurement_item_id = item_data.get('procurement_item_id')
            quantity_received = item_data.get('quantity_received')
            serial_numbers = item_data.get('serial_numbers', [])
            serial_units = item_data.get('serial_units', [])

            # Find the procurement item
            procurement_item = None
            for pi in self.items:
                if pi.id == procurement_item_id:
                    procurement_item = pi
                    break

            if not procurement_item:
                results.append(f'Item dengan ID {procurement_item_id} tidak ditemukan')
                all_success = False
                continue

            # Validate: tidak boleh melebihi quantity yang diminta
            if procurement_item.total_received + quantity_received > procurement_item.quantity:
                results.append(f'{procurement_item.item.name if procurement_item.item else "Item"}: Melebihi jumlah yang diminta')
                all_success = False
                continue

            # Validate quantity matches serial numbers count
            if serial_numbers and len(serial_numbers) != quantity_received:
                results.append(f'{procurement_item.item.name if procurement_item.item else "Item"}: Jumlah serial number tidak sesuai')
                all_success = False
                continue

            # Validate quantity matches serial units count
            if len(serial_units) != quantity_received:
                results.append(f'{procurement_item.item.name if procurement_item.item else "Item"}: Jumlah serial unit tidak sesuai')
                all_success = False
                continue

            # Add to receipt history
            success, message = procurement_item.add_receipt_to_history(quantity_received, serial_numbers, serial_units, user_id)
            if success:
                results.append(f'{procurement_item.item.name if procurement_item.item else "Item"}: {quantity_received} unit diterima')
            else:
                results.append(f'{procurement_item.item.name if procurement_item.item else "Item"}: {message}')
                all_success = False

        self.save()

        if all_success:
            if self.is_fully_received:
                return True, f'Semua barang berhasil diterima. Semua item sudah lengkap! Siap untuk diselesaikan.'
            else:
                return True, f'Barang berhasil diterima. Masih ada item yang belum lengkap.'
        else:
            return False, 'Sebagian barang gagal diterima: ' + '; '.join(results)

    def complete(self, user_id, warehouse_id=1):
        """Mark procurement as completed and add stock with item details"""
        from app.models.inventory import Stock, StockTransaction
        from app.models.master_data import ItemDetail
        import json

        # Validasi: harus status received dan semua barang sudah diterima
        if not self.is_fully_received:
            return False, f'Pengadaan belum bisa diselesaikan. Masih ada item yang belum lengkap.'

        try:
            items_created = 0
            items_skipped = 0
            total_quantity_added = 0

            print(f"=== DEBUG PROCUREMENT COMPLETE ===")
            print(f"Procurement ID: {self.id}")
            print(f"Items count: {len(self.items) if self.items else 0}")

            # Process each procurement item
            for procurement_item in self.items:
                print(f"\n--- Processing ProcurementItem #{procurement_item.id} ---")
                print(f"Item ID: {procurement_item.item_id}")
                print(f"Requested Quantity: {procurement_item.quantity}")
                print(f"Actual Quantity (received): {procurement_item.actual_quantity}")
                print(f"Serial Numbers: {procurement_item.serial_numbers}")

                if not procurement_item.item_id:
                    return False, f'Item {procurement_item.new_item_name if procurement_item.new_item_name else "Unknown"} harus diisi sebelum menyelesaikan pengadaan'

                # Get serial numbers
                serial_numbers = json.loads(procurement_item.serial_numbers) if procurement_item.serial_numbers else []
                print(f"Parsed serial numbers count: {len(serial_numbers)}")

                # Update warehouse_id for existing ItemDetails (created during receive_goods)
                # ItemDetails were created with warehouse_id=None, now assign them to the warehouse
                items_updated = 0
                for serial_number in serial_numbers:
                    existing_detail = ItemDetail.query.filter_by(serial_number=serial_number).first()
                    if existing_detail and existing_detail.warehouse_id is None:
                        existing_detail.warehouse_id = warehouse_id
                        existing_detail.save()
                        items_updated += 1
                        items_created += 1  # Count as "processed" for message
                    elif existing_detail and existing_detail.warehouse_id == warehouse_id:
                        items_created += 1  # Already in correct warehouse
                    elif existing_detail:
                        items_skipped += 1  # Already in different warehouse

                print(f"ItemDetails updated: {items_updated}, skipped: {items_skipped}")

                # Add to stock - count by actual serial numbers received
                stock = Stock.query.filter_by(
                    item_id=procurement_item.item_id,
                    warehouse_id=warehouse_id
                ).first()

                if not stock:
                    stock = Stock(item_id=procurement_item.item_id, warehouse_id=warehouse_id, quantity=0)
                    stock.save()

                # Use actual count of serial numbers received
                quantity_to_add = procurement_item.actual_quantity if procurement_item.actual_quantity else len(serial_numbers)
                print(f"Quantity to add to stock: {quantity_to_add}")
                total_quantity_added += quantity_to_add

                old_quantity = stock.quantity
                stock.add_stock(quantity_to_add)
                print(f"Stock updated: {old_quantity} -> {stock.quantity}")

                # Log transaction
                transaction = StockTransaction(
                    item_id=procurement_item.item_id,
                    warehouse_id=warehouse_id,
                    transaction_type='IN',
                    quantity=quantity_to_add,
                    note=f'Pengadaan #{self.id} - {procurement_item.total_received} unit'
                )
                transaction.save()

            print(f"\n=== COMPLETE ===")
            print(f"ItemDetails created: {items_created}")
            print(f"ItemDetails skipped: {items_skipped}")
            print(f"Total quantity added to stock: {total_quantity_added}")
            print(f"===============================\n")

            # Update procurement status
            self.status = 'completed'
            self.completed_by = user_id
            self.completion_date = datetime.utcnow()
            self.save()

            # Build success message - show actual quantity added to stock
            message_parts = []
            message_parts.append(f'{total_quantity_added} unit berhasil ditambahkan ke stok')
            if items_created > 0:
                message_parts.append(f'{items_created} item detail baru dibuat')
            if items_skipped > 0:
                message_parts.append(f'{items_skipped} serial number sudah ada sebelumnya')

            return True, f'Pengadaan berhasil diselesaikan. {", ".join(message_parts)}.'
        except Exception as e:
            import traceback
            print(f"ERROR in complete(): {str(e)}")
            print(traceback.format_exc())
            return False, f'Error menyelesaikan pengadaan: {str(e)}'

    def delete(self):
        """Delete procurement and all related items"""
        try:
            # Delete all procurement items first (cascade manually)
            for item in self.items:
                db.session.delete(item)

            # Then delete the procurement
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    def __repr__(self):
        return f'<Procurement #{self.id} Items:{len(self.items) if self.items else 0}>'
