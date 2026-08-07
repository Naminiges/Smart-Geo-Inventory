from io import BytesIO

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import false

from app import db
from app.forms.facility_request_forms import (
    FacilityAdministrationForm,
    FacilityLeadershipForm,
    FacilityOperationalForm,
    FacilityReceiptForm,
    FacilityRequestForm,
)
from app.models import (
    FacilityRequest,
    FacilityRequestItem,
    FacilityVerification,
    Distribution,
    Item,
    ItemDetail,
    UserUnit,
)
from app.services.facility_request_service import (
    add_approval,
    add_event,
    create_linked_asset_request,
    decode_signature,
    next_form_number,
    store_final_pdf,
    generate_pdf_bytes,
)
from app.utils.datetime_helper import get_wib_now
from app.utils.decorators import role_required


bp = Blueprint('facility_requests', __name__, url_prefix='/facility-requests')


def _request_context():
    return request.remote_addr, request.headers.get('User-Agent', '')


def _unit_ids_for_current_user():
    return [row.unit_id for row in UserUnit.query.filter_by(user_id=current_user.id).all()]


def _can_view(facility_request):
    if current_user.is_admin() or current_user.is_warehouse_staff():
        return True
    return current_user.is_unit_staff() and facility_request.unit_id in _unit_ids_for_current_user()


def _warehouse_choices():
    warehouses = current_user.get_accessible_warehouses()
    if current_user.warehouse and all(row.id != current_user.warehouse.id for row in warehouses):
        warehouses.append(current_user.warehouse)
    unique = {warehouse.id: warehouse for warehouse in warehouses}
    return [(warehouse.id, warehouse.name) for warehouse in sorted(unique.values(), key=lambda row: row.name)]


def _existing_assets_for_units(unit_ids):
    if not unit_ids:
        return []
    return (
        db.session.query(ItemDetail, Distribution)
        .join(Distribution, Distribution.item_detail_id == ItemDetail.id)
        .filter(
            Distribution.unit_id.in_(unit_ids),
            Distribution.is_draft.is_(False),
            ItemDetail.status.in_(['in_unit', 'used', 'maintenance', 'processing']),
        )
        .order_by(Distribution.unit_id, ItemDetail.serial_number)
        .all()
    )


def _parse_items(allowed_existing_asset_ids=None):
    item_ids = request.form.getlist('item_id[]')
    names = request.form.getlist('facility_name[]')
    specifications = request.form.getlist('specification[]')
    quantities = request.form.getlist('quantity[]')
    statuses = request.form.getlist('need_status[]')
    purposes = request.form.getlist('purpose[]')
    item_detail_ids = request.form.getlist('item_detail_id[]')
    allowed_existing_asset_ids = set(allowed_existing_asset_ids or [])

    if not names or len(names) > 6:
        raise ValueError('Formulir harus memiliki 1 sampai 6 fasilitas.')

    parsed = []
    for index, name in enumerate(names):
        name = (name or '').strip()
        try:
            quantity = int(quantities[index])
        except (ValueError, TypeError, IndexError) as exc:
            raise ValueError(f'Jumlah pada baris {index + 1} tidak valid.') from exc
        if quantity < 1 or quantity > 999:
            raise ValueError(f'Jumlah pada baris {index + 1} harus antara 1 dan 999.')

        item_id = None
        raw_item_id = item_ids[index].strip() if index < len(item_ids) else ''
        if raw_item_id:
            try:
                item_id = int(raw_item_id)
            except ValueError as exc:
                raise ValueError(f'Item katalog pada baris {index + 1} tidak valid.') from exc
            catalog_item = db.session.get(Item, item_id)
            if not catalog_item:
                raise ValueError(f'Item katalog pada baris {index + 1} tidak ditemukan.')

        item_detail_id = None
        raw_detail_id = item_detail_ids[index].strip() if index < len(item_detail_ids) else ''
        existing_detail = None
        if raw_detail_id:
            try:
                item_detail_id = int(raw_detail_id)
            except ValueError as exc:
                raise ValueError(f'Aset eksisting pada baris {index + 1} tidak valid.') from exc
            if item_detail_id not in allowed_existing_asset_ids:
                raise ValueError(f'Aset eksisting pada baris {index + 1} bukan milik unit yang dipilih.')
            existing_detail = db.session.get(ItemDetail, item_detail_id)
            if not existing_detail:
                raise ValueError(f'Aset eksisting pada baris {index + 1} tidak ditemukan.')
            if not item_id:
                item_id = existing_detail.item_id
            if not name:
                name = existing_detail.item.name

        if not name:
            raise ValueError(f'Nama fasilitas pada baris {index + 1} wajib diisi.')

        need_status = statuses[index] if index < len(statuses) else 'new'
        if need_status not in ('new', 'existing'):
            raise ValueError(f'Status fasilitas pada baris {index + 1} tidak valid.')

        parsed.append({
            'item_id': item_id,
            'item_detail_id': item_detail_id,
            'facility_name': name[:255],
            'specification': (specifications[index] if index < len(specifications) else '').strip(),
            'quantity': quantity,
            'need_status': need_status,
            'purpose': (purposes[index] if index < len(purposes) else '').strip(),
            'serial_number': existing_detail.serial_number if existing_detail else None,
        })
    return parsed


@bp.route('/')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def index():
    query = FacilityRequest.query
    if current_user.is_unit_staff():
        unit_ids = _unit_ids_for_current_user()
        query = query.filter(FacilityRequest.unit_id.in_(unit_ids)) if unit_ids else query.filter(false())
    elif current_user.is_warehouse_staff():
        query = query.filter(FacilityRequest.status.in_([
            'unit_signed', 'administratively_approved', 'leadership_approved',
            'in_fulfillment', 'warehouse_fulfillment', 'service_intake_pending',
            'service_in_progress', 'return_pending', 'replacement_pending',
            'replacement_in_fulfillment', 'replacement_old_received',
            'receipt_pending', 'completed', 'revision_requested', 'rejected'
        ]))

    status_filter = request.args.get('status', '').strip()
    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(FacilityRequest.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=20,
        error_out=False,
    )
    return render_template(
        'facility_requests/index.html',
        requests=pagination.items,
        pagination=pagination,
        status_filter=status_filter,
        page_icon='fas fa-file-signature',
        page_description='Formulir fasilitas unit dan persetujuan elektronik',
    )


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('unit_staff')
def create():
    unit_rows = UserUnit.query.filter_by(user_id=current_user.id).all()
    if not unit_rows:
        flash('Akun Anda belum terhubung ke unit.', 'danger')
        return redirect(url_for('facility_requests.index'))

    units = [row.unit for row in unit_rows]
    items = Item.query.order_by(Item.name).all()
    existing_assets = _existing_assets_for_units([unit.id for unit in units])
    form = FacilityRequestForm()

    if form.validate_on_submit():
        try:
            unit_id = request.form.get('unit_id', type=int)
            allowed = {unit.id: unit for unit in units}
            if unit_id not in allowed:
                raise ValueError('Unit yang dipilih tidak tersedia untuk akun Anda.')
            selected_existing_assets = [row for row in existing_assets if row[1].unit_id == unit_id]
            parsed_items = _parse_items({row[0].id for row in selected_existing_assets})
            if form.request_type.data == 'other' and not (form.other_request_type.data or '').strip():
                raise ValueError('Jenis kebutuhan lainnya wajib dijelaskan.')
            if form.request_type.data in ('repair_service', 'return', 'replacement') and selected_existing_assets:
                if any(not row['item_detail_id'] for row in parsed_items):
                    raise ValueError('Pilih aset/serial eksisting untuk setiap baris karena unit memiliki data aset terdaftar.')
            signature = decode_signature(form.signature_data.data)
            if not current_user.check_password(form.password.data):
                raise ValueError('Password konfirmasi tidak sesuai.')

            selected_unit = allowed[unit_id]
            facility_request = FacilityRequest(
                form_number=next_form_number(),
                unit_id=selected_unit.id,
                submitted_by=current_user.id,
                unit_name_snapshot=selected_unit.name,
                submitter_name_snapshot=current_user.name,
                submitter_email_snapshot=current_user.email,
                request_type=form.request_type.data,
                other_request_type=(form.other_request_type.data or '').strip() or None,
                priority=form.priority.data,
                justification=form.justification.data.strip(),
                impact_if_unavailable=form.impact_if_unavailable.data.strip(),
                status='unit_signed',
                version=1,
                submitted_at=get_wib_now(),
            )
            db.session.add(facility_request)
            db.session.flush()

            for row in parsed_items:
                db.session.add(FacilityRequestItem(facility_request_id=facility_request.id, **row))
            db.session.flush()

            ip_address, user_agent = _request_context()
            add_approval(
                facility_request, 'unit_supervisor', current_user, signature,
                ip_address=ip_address, user_agent=user_agent,
            )
            add_event(
                facility_request, 'UNIT_SUBMITTED_AND_SIGNED', current_user,
                old_status='draft', new_status='unit_signed',
                event_data={'form_number': facility_request.form_number},
                ip_address=ip_address, user_agent=user_agent,
            )
            db.session.commit()
            flash(f'{facility_request.form_number} berhasil diajukan dan ditandatangani.', 'success')
            return redirect(url_for('facility_requests.detail', id=facility_request.id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Failed to create facility request')
            flash('Formulir gagal disimpan. Periksa data dan coba kembali.', 'danger')
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return render_template(
        'facility_requests/create.html',
        form=form,
        units=units,
        catalog_items=items,
        existing_assets=existing_assets,
        page_icon='fas fa-file-circle-plus',
        page_description='Pengajuan atas nama unit dan tanda tangan Pemohon/Atasan Langsung',
    )


@bp.route('/<int:id>')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def detail(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if not _can_view(facility_request):
        abort(403)

    administration_form = FacilityAdministrationForm(prefix='administration')
    administration_form.warehouse_id.choices = _warehouse_choices() if current_user.is_warehouse_staff() else []
    leadership_form = FacilityLeadershipForm(prefix='leadership')
    receipt_form = FacilityReceiptForm(prefix='receipt')
    operational_form = FacilityOperationalForm(prefix='operation')
    return render_template(
        'facility_requests/detail.html',
        facility_request=facility_request,
        administration_form=administration_form,
        leadership_form=leadership_form,
        receipt_form=receipt_form,
        operational_form=operational_form,
        page_icon='fas fa-file-signature',
        page_description=f'Detail {facility_request.form_number}',
    )


@bp.route('/<int:id>/preview.pdf')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def preview_pdf(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if not _can_view(facility_request):
        abort(403)
    pdf_bytes = generate_pdf_bytes(facility_request)
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'{facility_request.form_number}-preview.pdf',
    )


@bp.route('/<int:id>/operational-action', methods=['POST'])
@login_required
@role_required('warehouse_staff')
def operational_action(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    actionable = {
        'warehouse_fulfillment', 'service_intake_pending', 'service_in_progress',
        'return_pending', 'replacement_pending', 'replacement_in_fulfillment',
    }
    if facility_request.status not in actionable:
        flash('Tidak ada tindakan operasional Administrasi untuk status formulir ini.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))

    allowed_warehouse_ids = {choice[0] for choice in _warehouse_choices()}
    if not facility_request.verification or facility_request.verification.warehouse_id not in allowed_warehouse_ids:
        abort(403)

    form = FacilityOperationalForm(prefix='operation')
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        return redirect(url_for('facility_requests.detail', id=id))

    try:
        if not current_user.check_password(form.password.data):
            raise ValueError('Password konfirmasi tidak sesuai.')

        now = get_wib_now()
        old_status = facility_request.status
        event_type = 'OPERATION_CONFIRMED'
        event_data = {'notes': form.notes.data}

        if old_status == 'warehouse_fulfillment':
            facility_request.released_by = current_user.id
            facility_request.released_at = now
            facility_request.status = 'receipt_pending'
            event_type = 'FACILITY_RELEASED_TO_UNIT'
        elif old_status == 'service_intake_pending':
            facility_request.warehouse_received_by = current_user.id
            facility_request.warehouse_received_at = now
            facility_request.status = 'service_in_progress'
            event_type = 'FACILITY_RECEIVED_FOR_SERVICE'
            for item in facility_request.items:
                if item.item_detail:
                    item.item_detail.status = 'maintenance'
        elif old_status == 'service_in_progress':
            facility_request.released_by = current_user.id
            facility_request.released_at = now
            facility_request.status = 'receipt_pending'
            event_type = 'SERVICE_COMPLETED_AND_RELEASED'
        elif old_status == 'return_pending':
            facility_request.warehouse_received_by = current_user.id
            facility_request.warehouse_received_at = now
            facility_request.received_by = current_user.id
            facility_request.received_at = now
            facility_request.status = 'completed'
            event_type = 'RETURN_RECEIVED_BY_WAREHOUSE'
            for item in facility_request.items:
                if item.item_detail:
                    item.item_detail.status = 'returned'
        elif old_status == 'replacement_in_fulfillment':
            facility_request.warehouse_received_by = current_user.id
            facility_request.warehouse_received_at = now
            facility_request.status = 'replacement_old_received'
            event_type = 'REPLACED_ASSET_RECEIVED_BY_WAREHOUSE'
            for item in facility_request.items:
                if item.item_detail:
                    item.item_detail.status = 'returned'
        elif old_status == 'replacement_pending':
            facility_request.warehouse_received_by = current_user.id
            facility_request.warehouse_received_at = now
            facility_request.released_by = current_user.id
            facility_request.released_at = now
            facility_request.status = 'receipt_pending'
            event_type = 'MANUAL_REPLACEMENT_RELEASED'
            for item in facility_request.items:
                if item.item_detail:
                    item.item_detail.status = 'returned'

        facility_request.operational_notes = form.notes.data
        ip_address, user_agent = _request_context()
        add_event(
            facility_request, event_type, current_user,
            old_status=old_status, new_status=facility_request.status,
            event_data=event_data, ip_address=ip_address, user_agent=user_agent,
        )
        db.session.flush()
        if facility_request.status == 'completed':
            store_final_pdf(facility_request, current_user, document_type='completed_form')
        db.session.commit()
        flash('Tindakan operasional berhasil dikonfirmasi tanpa tanda tangan tambahan.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to process facility operational action')
        flash('Tindakan operasional gagal diproses.', 'danger')
    return redirect(url_for('facility_requests.detail', id=id))


@bp.route('/<int:id>/administration-sign', methods=['POST'])
@login_required
@role_required('warehouse_staff')
def administration_sign(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if facility_request.status != 'unit_signed':
        flash('Formulir tidak sedang menunggu tanda tangan Administrasi.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))

    form = FacilityAdministrationForm(prefix='administration')
    form.warehouse_id.choices = _warehouse_choices()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        return redirect(url_for('facility_requests.detail', id=id))

    try:
        if not current_user.check_password(form.password.data):
            raise ValueError('Password konfirmasi tidak sesuai.')
        allowed_warehouse_ids = {choice[0] for choice in form.warehouse_id.choices}
        if form.warehouse_id.data not in allowed_warehouse_ids:
            raise ValueError('Anda tidak memiliki akses ke warehouse yang dipilih.')
        signature = decode_signature(form.signature_data.data)

        verification = FacilityVerification(
            facility_request_id=facility_request.id,
            warehouse_id=form.warehouse_id.data,
            availability=form.availability.data,
            device_condition=form.device_condition.data,
            facility_source=form.facility_source.data,
            recommendation=form.recommendation.data,
            estimated_completion=form.estimated_completion.data,
            realization_priority=form.realization_priority.data,
            notes=form.notes.data,
            verified_by=current_user.id,
            verified_at=get_wib_now(),
        )
        db.session.add(verification)
        db.session.flush()
        facility_request.verification = verification

        ip_address, user_agent = _request_context()
        add_approval(
            facility_request, 'administration', current_user, signature,
            notes=form.notes.data, ip_address=ip_address, user_agent=user_agent,
        )
        old_status = facility_request.status
        facility_request.status = 'administratively_approved'
        add_event(
            facility_request, 'ADMINISTRATION_SIGNED', current_user,
            old_status=old_status, new_status=facility_request.status,
            event_data={'warehouse_id': form.warehouse_id.data, 'recommendation': form.recommendation.data},
            ip_address=ip_address, user_agent=user_agent,
        )
        db.session.commit()
        flash('Verifikasi dan tanda tangan Administrasi berhasil disimpan.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to store administration signature')
        flash('Tanda tangan Administrasi gagal disimpan.', 'danger')
    return redirect(url_for('facility_requests.detail', id=id))


@bp.route('/<int:id>/leadership-sign', methods=['POST'])
@login_required
@role_required('admin')
def leadership_sign(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if facility_request.status != 'administratively_approved':
        flash('Formulir tidak sedang menunggu tanda tangan Pimpinan.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))

    form = FacilityLeadershipForm(prefix='leadership')
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        return redirect(url_for('facility_requests.detail', id=id))

    try:
        if not current_user.check_password(form.password.data):
            raise ValueError('Password konfirmasi tidak sesuai.')
        signature = decode_signature(form.signature_data.data)
        ip_address, user_agent = _request_context()
        add_approval(
            facility_request, 'leadership', current_user, signature,
            notes=form.notes.data, ip_address=ip_address, user_agent=user_agent,
        )
        old_status = facility_request.status
        linked_request = create_linked_asset_request(facility_request, current_user)
        if facility_request.request_type in ('new', 'addition'):
            facility_request.status = 'in_fulfillment' if linked_request else 'warehouse_fulfillment'
        elif facility_request.request_type == 'replacement':
            facility_request.status = 'replacement_in_fulfillment' if linked_request else 'replacement_pending'
        elif facility_request.request_type == 'repair_service':
            facility_request.status = 'service_intake_pending'
        elif facility_request.request_type == 'return':
            facility_request.status = 'return_pending'
        else:
            facility_request.status = 'warehouse_fulfillment'
        add_event(
            facility_request, 'LEADERSHIP_SIGNED', current_user,
            old_status=old_status, new_status=facility_request.status,
            event_data={'linked_asset_request_id': linked_request.id if linked_request else None},
            ip_address=ip_address, user_agent=user_agent,
        )
        db.session.flush()
        db.session.expire(facility_request, ['approvals'])
        store_final_pdf(facility_request, current_user, document_type='approved_form')
        db.session.commit()
        flash('Tanda tangan Pimpinan dan PDF berhasil dibuat.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to process leadership approval')
        flash('Persetujuan Pimpinan gagal diproses.', 'danger')
    return redirect(url_for('facility_requests.detail', id=id))


@bp.route('/<int:id>/confirm-receipt', methods=['POST'])
@login_required
@role_required('unit_staff')
def confirm_receipt(id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if not _can_view(facility_request):
        abort(403)
    if facility_request.request_type == 'return':
        flash('Pengembalian dikonfirmasi diterima oleh Administrasi/Warehouse.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))
    if facility_request.status not in ('in_fulfillment', 'receipt_pending', 'replacement_old_received'):
        flash('Formulir belum dapat dikonfirmasi penerimaannya.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))
    if facility_request.linked_asset_request and facility_request.linked_asset_request.status != 'completed':
        flash('Selesaikan distribusi pada permohonan aset terlebih dahulu.', 'warning')
        return redirect(url_for('facility_requests.detail', id=id))

    form = FacilityReceiptForm(prefix='receipt')
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        return redirect(url_for('facility_requests.detail', id=id))

    try:
        if not current_user.check_password(form.password.data):
            raise ValueError('Password konfirmasi tidak sesuai.')
        for item in facility_request.items:
            item.brand_type = request.form.get(f'brand_type_{item.id}', '').strip()[:255] or None
            item.inventory_number = request.form.get(f'inventory_number_{item.id}', '').strip()[:100] or None
            item.serial_number = request.form.get(f'serial_number_{item.id}', '').strip()[:100] or None
            condition = request.form.get(f'condition_{item.id}', '')
            if condition not in ('good', 'damaged'):
                raise ValueError(f'Kondisi untuk {item.facility_name} wajib dipilih.')
            item.handover_condition = condition
            item.handover_notes = request.form.get(f'handover_notes_{item.id}', '').strip() or None

        old_status = facility_request.status
        if not facility_request.released_by and facility_request.linked_asset_request:
            linked = facility_request.linked_asset_request
            facility_request.released_by = linked.distributed_by or linked.verified_by
            facility_request.released_at = linked.distributed_at or linked.received_at or get_wib_now()
        facility_request.status = 'completed'
        facility_request.received_by = current_user.id
        facility_request.received_at = get_wib_now()
        facility_request.receipt_notes = form.receipt_notes.data
        facility_request.user_statement_accepted = True
        for item in facility_request.items:
            if item.item_detail and facility_request.request_type == 'repair_service':
                item.item_detail.status = 'in_unit'
        ip_address, user_agent = _request_context()
        add_event(
            facility_request, 'RECEIPT_CONFIRMED', current_user,
            old_status=old_status, new_status='completed',
            event_data={'statement_accepted': True},
            ip_address=ip_address, user_agent=user_agent,
        )
        db.session.flush()
        store_final_pdf(facility_request, current_user, document_type='completed_form')
        db.session.commit()
        flash('Penerimaan fasilitas berhasil dikonfirmasi.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to confirm facility receipt')
        flash('Konfirmasi penerimaan gagal diproses.', 'danger')
    return redirect(url_for('facility_requests.detail', id=id))


@bp.route('/<int:id>/approval/<int:approval_id>/signature')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def signature_image(id, approval_id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if not _can_view(facility_request):
        abort(403)
    approval = next((row for row in facility_request.approvals if row.id == approval_id), None)
    if not approval:
        abort(404)
    return send_file(BytesIO(approval.signature_data), mimetype=approval.signature_mime, as_attachment=False)


@bp.route('/<int:id>/document/<int:document_id>/download')
@login_required
@role_required('unit_staff', 'warehouse_staff', 'admin')
def download_document(id, document_id):
    facility_request = FacilityRequest.query.get_or_404(id)
    if not _can_view(facility_request):
        abort(403)
    document = next((row for row in facility_request.documents if row.id == document_id), None)
    if not document:
        abort(404)
    return send_file(
        BytesIO(document.file_data),
        mimetype=document.mime_type,
        as_attachment=True,
        download_name=document.filename,
    )
