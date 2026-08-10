from app import db
from app.models.base import BaseModel
from app.utils.datetime_helper import get_wib_now


class FacilityRequest(BaseModel):
    """Formulir fasilitas yang membungkus workflow persetujuan dan fulfillment."""

    __tablename__ = 'facility_requests'

    form_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False, index=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    unit_name_snapshot = db.Column(db.String(255), nullable=False)
    submitter_name_snapshot = db.Column(db.String(100), nullable=False)
    submitter_email_snapshot = db.Column(db.String(120))

    request_type = db.Column(db.String(30), nullable=False)
    other_request_type = db.Column(db.String(255))
    priority = db.Column(db.String(20), nullable=False, default='normal')
    justification = db.Column(db.Text, nullable=False)
    impact_if_unavailable = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(40), nullable=False, default='unit_signed', index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    submitted_at = db.Column(db.DateTime, nullable=False, default=get_wib_now)

    linked_asset_request_id = db.Column(db.Integer, db.ForeignKey('asset_requests.id'))
    warehouse_received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    warehouse_received_at = db.Column(db.DateTime)
    released_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    released_at = db.Column(db.DateTime)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    received_at = db.Column(db.DateTime)
    receipt_notes = db.Column(db.Text)
    operational_notes = db.Column(db.Text)
    user_statement_accepted = db.Column(db.Boolean, nullable=False, default=False)

    unit = db.relationship('Unit', backref='facility_requests')
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='facility_requests_submitted')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='facility_requests_received')
    warehouse_receiver = db.relationship('User', foreign_keys=[warehouse_received_by], backref='facility_returns_received')
    releaser = db.relationship('User', foreign_keys=[released_by], backref='facility_requests_released')
    linked_asset_request = db.relationship('AssetRequest', foreign_keys=[linked_asset_request_id])
    items = db.relationship(
        'FacilityRequestItem',
        back_populates='facility_request',
        cascade='all, delete-orphan',
        order_by='FacilityRequestItem.id'
    )
    verification = db.relationship(
        'FacilityVerification',
        back_populates='facility_request',
        uselist=False,
        cascade='all, delete-orphan'
    )
    approvals = db.relationship(
        'FacilityApproval',
        back_populates='facility_request',
        cascade='all, delete-orphan',
        order_by='FacilityApproval.signed_at'
    )
    documents = db.relationship(
        'FacilityDocument',
        back_populates='facility_request',
        cascade='all, delete-orphan',
        order_by='FacilityDocument.created_at'
    )
    events = db.relationship(
        'FacilityRequestEvent',
        back_populates='facility_request',
        cascade='all, delete-orphan',
        order_by='FacilityRequestEvent.created_at'
    )

    @property
    def status_display(self):
        return {
            'unit_signed': 'Menunggu Administrasi',
            'administratively_approved': 'Menunggu Pimpinan',
            'leadership_approved': 'Disetujui Pimpinan',
            'in_fulfillment': 'Dalam Pemenuhan',
            'warehouse_fulfillment': 'Menunggu Penyerahan Administrasi',
            'service_intake_pending': 'Menunggu Penerimaan untuk Servis',
            'service_in_progress': 'Dalam Proses Servis',
            'return_pending': 'Menunggu Penerimaan Pengembalian',
            'replacement_pending': 'Menunggu Proses Penggantian',
            'replacement_in_fulfillment': 'Penggantian dalam Pemenuhan',
            'replacement_old_received': 'Aset Lama Diterima; Menunggu Pengganti',
            'receipt_pending': 'Menunggu Penerimaan',
            'completed': 'Selesai',
            'revision_requested': 'Perlu Revisi',
            'rejected': 'Ditolak',
            'cancelled': 'Dibatalkan',
        }.get(self.status, self.status.replace('_', ' ').title())

    @property
    def request_type_display(self):
        return {
            'new': 'Pengajuan fasilitas baru',
            'addition': 'Penambahan fasilitas',
            'repair_service': 'Perbaikan/servis',
            'return': 'Pengembalian fasilitas',
            'replacement': 'Penggantian fasilitas',
            'other': self.other_request_type or 'Lainnya',
        }.get(self.request_type, self.request_type.replace('_', ' ').title())

    @property
    def latest_document(self):
        return self.documents[-1] if self.documents else None

    def approval_for(self, stage):
        return next((approval for approval in self.approvals if approval.stage == stage), None)


class FacilityRequestItem(BaseModel):
    """Satu sumber item dari pengajuan sampai serah-terima."""

    __tablename__ = 'facility_request_items'

    facility_request_id = db.Column(db.Integer, db.ForeignKey('facility_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'))
    facility_name = db.Column(db.String(255), nullable=False)
    specification = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False)
    need_status = db.Column(db.String(20), nullable=False, default='new')
    purpose = db.Column(db.Text)

    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'))
    brand_type = db.Column(db.String(255))
    inventory_number = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    handover_condition = db.Column(db.String(30))
    handover_notes = db.Column(db.Text)
    linked_asset_request_item_id = db.Column(db.Integer, db.ForeignKey('asset_request_items.id'))

    facility_request = db.relationship('FacilityRequest', back_populates='items')
    item = db.relationship('Item')
    item_detail = db.relationship('ItemDetail')
    linked_asset_request_item = db.relationship('AssetRequestItem')


class FacilityVerification(BaseModel):
    __tablename__ = 'facility_verifications'

    facility_request_id = db.Column(db.Integer, db.ForeignKey('facility_requests.id', ondelete='CASCADE'), nullable=False, unique=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    availability = db.Column(db.String(30), nullable=False)
    device_condition = db.Column(db.String(30), nullable=False)
    facility_source = db.Column(db.String(30), nullable=False)
    recommendation = db.Column(db.String(30), nullable=False)
    estimated_completion = db.Column(db.Date)
    realization_priority = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    verified_at = db.Column(db.DateTime, nullable=False, default=get_wib_now)

    facility_request = db.relationship('FacilityRequest', back_populates='verification')
    warehouse = db.relationship('Warehouse')
    verifier = db.relationship('User')


class FacilityApproval(BaseModel):
    __tablename__ = 'facility_approvals'

    facility_request_id = db.Column(db.Integer, db.ForeignKey('facility_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    stage = db.Column(db.String(30), nullable=False)
    expected_role = db.Column(db.String(50), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    signed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    signer_name_snapshot = db.Column(db.String(100), nullable=False)
    signer_role_snapshot = db.Column(db.String(50), nullable=False)
    decision = db.Column(db.String(20), nullable=False, default='approved')
    notes = db.Column(db.Text)
    signature_data = db.Column(db.LargeBinary, nullable=False)
    signature_mime = db.Column(db.String(50), nullable=False, default='image/png')
    document_hash = db.Column(db.String(64), nullable=False)
    consent_text = db.Column(db.Text, nullable=False)
    consent_version = db.Column(db.String(20), nullable=False, default='1.0')
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    signed_at = db.Column(db.DateTime, nullable=False, default=get_wib_now)

    facility_request = db.relationship('FacilityRequest', back_populates='approvals')
    signer = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('facility_request_id', 'stage', 'version', name='uq_facility_approval_stage_version'),
    )


class FacilityDocument(BaseModel):
    __tablename__ = 'facility_documents'

    facility_request_id = db.Column(db.Integer, db.ForeignKey('facility_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    document_type = db.Column(db.String(30), nullable=False, default='approved_form')
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False, default='application/pdf')
    file_size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False, index=True)
    file_data = db.Column(db.LargeBinary, nullable=False)
    is_final = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    facility_request = db.relationship('FacilityRequest', back_populates='documents')
    creator = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('facility_request_id', 'version', 'document_type', name='uq_facility_document_version_type'),
    )


class FacilityRequestEvent(BaseModel):
    __tablename__ = 'facility_request_events'

    facility_request_id = db.Column(db.Integer, db.ForeignKey('facility_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor_name_snapshot = db.Column(db.String(100), nullable=False)
    actor_role_snapshot = db.Column(db.String(50))
    old_status = db.Column(db.String(40))
    new_status = db.Column(db.String(40))
    event_data = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))

    facility_request = db.relationship('FacilityRequest', back_populates='events')
    actor = db.relationship('User')
