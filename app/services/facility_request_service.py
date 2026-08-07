import base64
import hashlib
import json
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from sqlalchemy import text

from app import db
from app.models import (
    AssetRequest,
    AssetRequestItem,
    FacilityApproval,
    FacilityDocument,
    FacilityRequestEvent,
)
from app.utils.datetime_helper import get_wib_now


STAGE_ROLE = {
    'unit_supervisor': 'unit_staff',
    'administration': 'warehouse_staff',
    'leadership': 'admin',
}

STAGE_LABEL = {
    'unit_supervisor': 'Pemohon/Atasan Langsung',
    'administration': 'Administrasi',
    'leadership': 'Pimpinan',
}

CONSENT_TEXT = {
    'unit_supervisor': 'Saya mengajukan dan menyetujui isi formulir ini atas nama unit sebagai Pemohon/Atasan Langsung.',
    'administration': 'Saya telah memverifikasi data, ketersediaan, dan rekomendasi pada formulir ini sebagai Administrasi.',
    'leadership': 'Saya menyetujui keputusan pada formulir ini sebagai Pimpinan.',
}


def next_form_number():
    sequence_value = db.session.execute(text("SELECT nextval('facility_form_number_seq')")).scalar_one()
    return f'DITSINTEK-FORM-{sequence_value:03d}'


def decode_signature(data_url, max_bytes=750 * 1024):
    if not data_url or not data_url.startswith('data:image/png;base64,'):
        raise ValueError('Format tanda tangan tidak valid. Gunakan signature pad yang tersedia.')

    try:
        raw = base64.b64decode(data_url.split(',', 1)[1], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('Data tanda tangan tidak dapat dibaca.') from exc

    if not raw or len(raw) > max_bytes:
        raise ValueError('Ukuran tanda tangan tidak valid atau melebihi 750 KB.')
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Tanda tangan harus berupa gambar PNG.')

    try:
        image = PILImage.open(BytesIO(raw))
        image.verify()
        image = PILImage.open(BytesIO(raw)).convert('RGBA')
        if image.width < 100 or image.height < 50 or image.width > 2400 or image.height > 1200:
            raise ValueError('Dimensi tanda tangan tidak valid.')

        # A canvas that contains only white/transparent pixels is not a signature.
        flattened = PILImage.new('RGBA', image.size, 'white')
        flattened.alpha_composite(image)
        grayscale = flattened.convert('L')
        minimum, maximum = grayscale.getextrema()
        if minimum > 245 or minimum == maximum:
            raise ValueError('Tanda tangan masih kosong.')

        output = BytesIO()
        image.save(output, format='PNG', optimize=True)
        normalized = output.getvalue()
        if len(normalized) > max_bytes:
            raise ValueError('Tanda tangan hasil validasi melebihi 750 KB.')
        return normalized
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('File tanda tangan rusak atau tidak didukung.') from exc


def canonical_payload(facility_request):
    verification = facility_request.verification
    payload = {
        'form_number': facility_request.form_number,
        'version': facility_request.version,
        'unit': {
            'id': facility_request.unit_id,
            'name': facility_request.unit_name_snapshot,
            'submitted_by': facility_request.submitted_by,
            'submitter_name': facility_request.submitter_name_snapshot,
            'submitter_email': facility_request.submitter_email_snapshot,
        },
        'request_type': facility_request.request_type,
        'other_request_type': facility_request.other_request_type,
        'priority': facility_request.priority,
        'justification': facility_request.justification,
        'impact_if_unavailable': facility_request.impact_if_unavailable,
        'items': [
            {
                'id': item.id,
                'item_id': item.item_id,
                'item_detail_id': item.item_detail_id,
                'facility_name': item.facility_name,
                'specification': item.specification,
                'quantity': item.quantity,
                'need_status': item.need_status,
                'purpose': item.purpose,
                'serial_number': item.serial_number,
                'handover_condition': item.handover_condition,
            }
            for item in facility_request.items
        ],
        'operations': {
            'warehouse_received_by': facility_request.warehouse_received_by,
            'warehouse_received_at': facility_request.warehouse_received_at.isoformat() if facility_request.warehouse_received_at else None,
            'released_by': facility_request.released_by,
            'released_at': facility_request.released_at.isoformat() if facility_request.released_at else None,
            'received_by': facility_request.received_by,
            'received_at': facility_request.received_at.isoformat() if facility_request.received_at else None,
            'operational_notes': facility_request.operational_notes,
            'receipt_notes': facility_request.receipt_notes,
        },
        'verification': None if not verification else {
            'warehouse_id': verification.warehouse_id,
            'availability': verification.availability,
            'device_condition': verification.device_condition,
            'facility_source': verification.facility_source,
            'recommendation': verification.recommendation,
            'estimated_completion': verification.estimated_completion.isoformat() if verification.estimated_completion else None,
            'realization_priority': verification.realization_priority,
            'notes': verification.notes,
            'verified_by': verification.verified_by,
            'verified_at': verification.verified_at.isoformat(),
        },
        'prior_approvals': [
            {
                'stage': approval.stage,
                'signed_by': approval.signed_by,
                'signed_at': approval.signed_at.isoformat(),
                'document_hash': approval.document_hash,
                'decision': approval.decision,
            }
            for approval in facility_request.approvals
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def payload_hash(facility_request):
    return hashlib.sha256(canonical_payload(facility_request).encode('utf-8')).hexdigest()


def add_event(facility_request, event_type, actor, old_status=None, new_status=None,
              event_data=None, ip_address=None, user_agent=None):
    event = FacilityRequestEvent(
        facility_request_id=facility_request.id,
        event_type=event_type,
        actor_id=actor.id if actor else None,
        actor_name_snapshot=actor.name if actor else 'System',
        actor_role_snapshot=actor.role if actor else 'system',
        old_status=old_status,
        new_status=new_status,
        event_data=event_data,
        ip_address=ip_address,
        user_agent=(user_agent or '')[:500],
    )
    db.session.add(event)
    return event


def add_approval(facility_request, stage, actor, signature_data, notes=None,
                 ip_address=None, user_agent=None):
    expected_role = STAGE_ROLE[stage]
    if actor.role != expected_role:
        raise ValueError(f'Tahap {STAGE_LABEL[stage]} hanya dapat ditandatangani role {expected_role}.')

    duplicate = FacilityApproval.query.filter_by(
        facility_request_id=facility_request.id,
        stage=stage,
        version=facility_request.version,
    ).first()
    if duplicate:
        raise ValueError(f'Tahap {STAGE_LABEL[stage]} sudah ditandatangani.')

    approval = FacilityApproval(
        facility_request_id=facility_request.id,
        stage=stage,
        expected_role=expected_role,
        version=facility_request.version,
        signed_by=actor.id,
        signer_name_snapshot=actor.name,
        signer_role_snapshot=actor.role,
        decision='approved',
        notes=notes,
        signature_data=signature_data,
        signature_mime='image/png',
        document_hash=payload_hash(facility_request),
        consent_text=CONSENT_TEXT[stage],
        consent_version='1.0',
        ip_address=ip_address,
        user_agent=(user_agent or '')[:500],
        signed_at=get_wib_now(),
    )
    db.session.add(approval)
    db.session.flush()
    return approval


def create_linked_asset_request(facility_request, admin_user):
    if facility_request.linked_asset_request_id:
        return facility_request.linked_asset_request

    if facility_request.request_type not in ('new', 'addition', 'replacement'):
        return None

    catalog_items = [item for item in facility_request.items if item.item_id]
    if not catalog_items:
        return None

    verification = facility_request.verification
    warehouse_id = verification.warehouse_id if verification else None
    linked = AssetRequest(
        unit_id=facility_request.unit_id,
        requested_by=facility_request.submitted_by,
        request_date=get_wib_now(),
        verified_by=admin_user.id,
        verified_at=get_wib_now(),
        verification_notes=f'Disetujui melalui {facility_request.form_number}',
        status='verified',
        request_notes=(
            f'Permohonan otomatis dari formulir fasilitas {facility_request.form_number}.\n'
            f'Alasan: {facility_request.justification}'
        ),
        notes=f'warehouse_id:{warehouse_id}' if warehouse_id else None,
    )
    db.session.add(linked)
    db.session.flush()

    for source_item in catalog_items:
        linked_item = AssetRequestItem(
            asset_request_id=linked.id,
            item_id=source_item.item_id,
            quantity=source_item.quantity,
            room_notes=source_item.specification,
            status='pending',
        )
        db.session.add(linked_item)
        db.session.flush()
        source_item.linked_asset_request_item_id = linked_item.id

    facility_request.linked_asset_request_id = linked.id
    return linked


def _generate_pdf_bytes_legacy(facility_request):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=facility_request.form_number,
        author='DITSINTEK USU',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterSmall', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='Small', parent=styles['Normal'], fontSize=8, leading=10))

    def pdf_text(value, fallback='-'):
        """Escape user-controlled values before ReportLab parses paragraph markup."""
        text_value = str(value) if value not in (None, '') else fallback
        return escape(text_value).replace('\n', '<br/>')

    story = [
        Paragraph('<b>UNIVERSITAS SUMATERA UTARA</b>', styles['Title']),
        Paragraph('Direktorat Sistem Informasi dan Pengembangan Teknologi', styles['Heading2']),
        Paragraph('<b>FORMULIR FASILITAS UNIT</b>', styles['Heading1']),
        Paragraph(f'Nomor: <b>{pdf_text(facility_request.form_number)}</b>', styles['Normal']),
        Spacer(1, 0.3 * cm),
    ]

    request_type = {'new': 'Pengajuan fasilitas baru', 'addition': 'Penambahan fasilitas'}.get(
        facility_request.request_type, facility_request.request_type
    )
    priority = {'normal': 'Normal', 'important': 'Penting', 'urgent': 'Mendesak'}.get(
        facility_request.priority, facility_request.priority
    )
    summary_rows = [
        ['Unit', Paragraph(pdf_text(facility_request.unit_name_snapshot), styles['Normal'])],
        ['Akun pengirim', Paragraph(pdf_text(f'{facility_request.submitter_name_snapshot} ({facility_request.submitter_email_snapshot or "-"})'), styles['Normal'])],
        ['Jenis formulir', request_type],
        ['Prioritas', priority],
        ['Tanggal pengajuan', facility_request.submitted_at.strftime('%d/%m/%Y %H:%M')],
    ]
    if facility_request.received_at:
        receiver_name = facility_request.receiver.name if facility_request.receiver else facility_request.submitter_name_snapshot
        summary_rows.extend([
            ['Diterima oleh', Paragraph(pdf_text(receiver_name), styles['Normal'])],
            ['Tanggal penerimaan', facility_request.received_at.strftime('%d/%m/%Y %H:%M')],
            ['Catatan penerimaan', Paragraph(pdf_text(facility_request.receipt_notes), styles['Normal'])],
        ])
    summary = Table(summary_rows, colWidths=[4 * cm, 13 * cm])
    summary.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECFDF5')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([summary, Spacer(1, 0.35 * cm), Paragraph('<b>Daftar fasilitas</b>', styles['Heading3'])])

    include_handover = facility_request.status == 'completed' or bool(facility_request.received_at)
    item_rows = [['No', 'Fasilitas', 'Spesifikasi', 'Jumlah', 'Status', 'Keperluan']]
    if include_handover:
        item_rows[0].append('Hasil serah terima')
    for index, item in enumerate(facility_request.items, 1):
        item_row = [
            str(index),
            Paragraph(pdf_text(item.facility_name), styles['Small']),
            Paragraph(pdf_text(item.specification), styles['Small']),
            str(item.quantity),
            'Baru' if item.need_status == 'new' else 'Eksisting',
            Paragraph(pdf_text(item.purpose), styles['Small']),
        ]
        if include_handover:
            handover_lines = [
                f'Merek/tipe: {item.brand_type or "-"}',
                f'No. inventaris: {item.inventory_number or "-"}',
                f'Serial: {item.serial_number or "-"}',
                f'Kondisi: {"Baik" if item.handover_condition == "good" else "Rusak" if item.handover_condition == "damaged" else "-"}',
                f'Catatan: {item.handover_notes or "-"}',
            ]
            item_row.append(Paragraph(pdf_text('\n'.join(handover_lines)), styles['Small']))
        item_rows.append(item_row)
    column_widths = (
        [0.6 * cm, 2.5 * cm, 2.8 * cm, 1.0 * cm, 1.4 * cm, 3.6 * cm, 5.1 * cm]
        if include_handover
        else [0.7 * cm, 3.4 * cm, 4.1 * cm, 1.3 * cm, 1.7 * cm, 5.8 * cm]
    )
    items_table = Table(item_rows, colWidths=column_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#047857')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.extend([
        items_table,
        Spacer(1, 0.35 * cm),
        Paragraph('<b>Alasan/justifikasi kebutuhan</b>', styles['Heading3']),
        Paragraph(pdf_text(facility_request.justification), styles['Normal']),
        Spacer(1, 0.2 * cm),
        Paragraph('<b>Dampak apabila fasilitas tidak tersedia</b>', styles['Heading3']),
        Paragraph(pdf_text(facility_request.impact_if_unavailable), styles['Normal']),
        Spacer(1, 0.35 * cm),
    ])

    if facility_request.verification:
        verification = facility_request.verification
        verification_table = Table([
            ['Warehouse', Paragraph(pdf_text(verification.warehouse.name if verification.warehouse else None), styles['Small'])],
            ['Ketersediaan', verification.availability.replace('_', ' ').title()],
            ['Kondisi', verification.device_condition.replace('_', ' ').title()],
            ['Sumber', verification.facility_source.replace('_', ' ').title()],
            ['Rekomendasi', verification.recommendation.replace('_', ' ').title()],
            ['Prioritas realisasi', verification.realization_priority.replace('_', ' ').title()],
            ['Estimasi', verification.estimated_completion.strftime('%d/%m/%Y') if verification.estimated_completion else '-'],
            ['Catatan', Paragraph(pdf_text(verification.notes), styles['Small'])],
        ], colWidths=[4 * cm, 13 * cm])
        verification_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.extend([Paragraph('<b>Verifikasi Administrasi</b>', styles['Heading3']), verification_table, Spacer(1, 0.4 * cm)])

    approval_cells = []
    for stage in ('unit_supervisor', 'administration', 'leadership'):
        approval = facility_request.approval_for(stage)
        cell = [Paragraph(f'<b>{STAGE_LABEL[stage]}</b>', styles['CenterSmall'])]
        if approval:
            signature = Image(BytesIO(approval.signature_data), width=4.2 * cm, height=1.8 * cm)
            cell.extend([
                signature,
                Paragraph(pdf_text(approval.signer_name_snapshot), styles['CenterSmall']),
                Paragraph(approval.signed_at.strftime('%d/%m/%Y %H:%M'), styles['CenterSmall']),
                Paragraph(f'Hash: {approval.document_hash[:12]}…', styles['CenterSmall']),
            ])
        else:
            cell.append(Paragraph('Belum ditandatangani', styles['CenterSmall']))
        approval_cells.append(cell)

    approval_table = Table([approval_cells], colWidths=[5.65 * cm] * 3)
    approval_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.extend([Paragraph('<b>Tanda Tangan Elektronik POC</b>', styles['Heading3']), approval_table])

    document.build(story)
    return buffer.getvalue()


def generate_pdf_bytes(facility_request):
    """Generate a progressive PDF styled after the supplied DITSINTEK USU form."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    brand_green = colors.HexColor('#006B3C')
    light_green = colors.HexColor('#E6EFE8')
    border_gray = colors.HexColor('#777777')
    muted_gray = colors.HexColor('#555555')
    content_width = 18.5 * cm
    logo_path = Path(__file__).resolve().parents[1] / 'static' / 'img' / 'logo-usu.png'

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.25 * cm,
        leftMargin=1.25 * cm,
        topMargin=3.25 * cm,
        bottomMargin=1.15 * cm,
        title=facility_request.form_number,
        author='DITSINTEK USU',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='FormSmall', parent=styles['Normal'], fontSize=7.2, leading=8.8, textColor=colors.black))
    styles.add(ParagraphStyle(name='FormCenter', parent=styles['FormSmall'], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='FormTableHeader', parent=styles['FormCenter'], fontSize=6.6, leading=7.6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FormLabel', parent=styles['FormSmall'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='FormTitle', parent=styles['Heading1'], fontSize=13.5, leading=16, alignment=TA_CENTER, spaceAfter=2, textColor=brand_green))
    styles.add(ParagraphStyle(name='FormNumber', parent=styles['FormCenter'], fontSize=10.5, leading=13, textColor=brand_green))
    styles.add(ParagraphStyle(name='FormNote', parent=styles['FormSmall'], fontSize=6.5, leading=7.5, textColor=muted_gray, fontName='Helvetica-Oblique'))
    styles.add(ParagraphStyle(name='HeaderInstitution', parent=styles['Normal'], fontSize=8.8, leading=10.8, textColor=colors.black))
    styles.add(ParagraphStyle(name='HeaderContact', parent=styles['Normal'], fontSize=7.2, leading=8.6, textColor=colors.black))

    def safe(value, fallback='-'):
        text_value = str(value) if value not in (None, '') else fallback
        return escape(text_value).replace('\n', '<br/>')

    def p(value, style='FormSmall', fallback='-'):
        return Paragraph(safe(value, fallback), styles[style])

    def rawp(markup, style='FormSmall'):
        return Paragraph(markup, styles[style])

    def section(title):
        bar = Table(
            [[Paragraph(f'<b><font color="white">{safe(title, "")}</font></b>', styles['FormSmall'])]],
            colWidths=[content_width],
        )
        bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), brand_green),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        bar.spaceBefore = 0.22 * cm
        bar.spaceAfter = 0.14 * cm
        return bar

    def grid_style(header=False):
        commands = [
            ('GRID', (0, 0), (-1, -1), 0.55, border_gray),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ]
        if header:
            commands.extend([
                ('BACKGROUND', (0, 0), (-1, 0), light_green),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ])
        return TableStyle(commands)

    def checkbox(selected):
        return '<b>[X]</b>' if selected else '[ ]'

    generated_at = get_wib_now().strftime('%d/%m/%Y %H:%M WIB')

    def draw_page_chrome(canvas, doc):
        canvas.saveState()
        header_top = A4[1] - 0.55 * cm
        if logo_path.exists():
            canvas.drawImage(
                ImageReader(str(logo_path)),
                1.25 * cm,
                header_top - 2.05 * cm,
                width=2.05 * cm,
                height=2.05 * cm,
                preserveAspectRatio=True,
                mask='auto',
            )

        institution = Paragraph(
            'Universitas<br/>Sumatera Utara<br/><b>Direktorat Sistem Informasi &amp;<br/>Pengembangan Teknologi</b>',
            styles['HeaderInstitution'],
        )
        institution.wrapOn(canvas, 6.0 * cm, 2.2 * cm)
        institution.drawOn(canvas, 3.55 * cm, header_top - 1.9 * cm)

        address = Paragraph(
            '<b>Alamat</b><br/>Jalan Universitas No. 9<br/>Padang Bulan, Kec. Medan Baru,<br/>Kota Medan, Sumatera Utara 20155',
            styles['HeaderContact'],
        )
        address.wrapOn(canvas, 5.1 * cm, 2.2 * cm)
        address.drawOn(canvas, 10.4 * cm, header_top - 1.78 * cm)

        contact = Paragraph(
            '<b>Email:</b> ditsintek@usu.ac.id<br/><b>Telepon:</b> (061) 8213793',
            styles['HeaderContact'],
        )
        contact.wrapOn(canvas, 4.3 * cm, 2.2 * cm)
        contact.drawOn(canvas, 16.0 * cm, header_top - 1.28 * cm)

        line_y = A4[1] - 2.72 * cm
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1.1)
        canvas.line(1.25 * cm, line_y, A4[0] - 1.25 * cm, line_y)

        canvas.setFont('Helvetica', 6.6)
        canvas.setFillColor(muted_gray)
        canvas.drawString(1.25 * cm, 0.55 * cm, f'{facility_request.form_number} | Status: {facility_request.status_display} | Dibuat: {generated_at}')
        canvas.drawRightString(A4[0] - 1.25 * cm, 0.55 * cm, f'Halaman {doc.page}')
        canvas.restoreState()

    story = []
    story.extend([
        Paragraph('<b>FORMULIR FASILITAS UNIT</b>', styles['FormTitle']),
        Paragraph(f'<b>NOMOR: {safe(facility_request.form_number)}</b> &nbsp;&nbsp; VERSI: {facility_request.version}', styles['FormNumber']),
        Spacer(1, 0.18 * cm),
    ])

    story.append(section('A. JENIS FORMULIR'))
    request_types = [
        ('new', 'Pengajuan fasilitas baru'),
        ('addition', 'Penambahan fasilitas'),
        ('repair_service', 'Perbaikan/servis'),
        ('return', 'Pengembalian fasilitas'),
        ('replacement', 'Penggantian fasilitas'),
        ('other', f'Lainnya: {facility_request.other_request_type or "-"}'),
    ]
    type_markup = {
        value: f'{checkbox(facility_request.request_type == value)} {safe(label)}'
        for value, label in request_types
    }
    priority_labels = {'normal': 'Normal', 'important': 'Penting', 'urgent': 'Mendesak'}
    priority_text = '&nbsp;&nbsp;'.join(
        f'{checkbox(facility_request.priority == value)} {label}'
        for value, label in priority_labels.items()
    )
    type_table = Table([
        [
            rawp(f'{type_markup["new"]}&nbsp;&nbsp; {type_markup["addition"]}<br/>{type_markup["replacement"]}'),
            rawp(f'{type_markup["repair_service"]}&nbsp;&nbsp; {type_markup["return"]}<br/>{type_markup["other"]}'),
        ],
        [
            rawp(f'<b>Tingkat Prioritas:</b>&nbsp;&nbsp; {priority_text}'),
            rawp('<b>Peran Pengaju:</b>&nbsp;&nbsp; Unit / Atasan Langsung'),
        ],
    ], colWidths=[9.25 * cm, 9.25 * cm])
    type_table.setStyle(grid_style())
    type_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(type_table)

    story.append(section('B. DATA UNIT DAN AKUN PENGIRIM'))
    identity = Table([
        [rawp('<b>Unit</b>'), p(facility_request.unit_name_snapshot), rawp('<b>Tanggal pengajuan</b>'), p(facility_request.submitted_at.strftime('%d/%m/%Y %H:%M'))],
        [rawp('<b>Pemohon/Atasan langsung</b>'), p(facility_request.submitter_name_snapshot), rawp('<b>Email USU</b>'), p(facility_request.submitter_email_snapshot)],
    ], colWidths=[3.15 * cm, 6.1 * cm, 3.15 * cm, 6.1 * cm])
    identity.setStyle(grid_style())
    identity.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), light_green),
        ('BACKGROUND', (2, 0), (2, -1), light_green),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(identity)

    story.append(section('C. DAFTAR FASILITAS YANG DIAJUKAN / DIKELOLA'))
    include_realization = any(
        item.brand_type or item.inventory_number or item.serial_number or item.handover_condition or item.handover_notes
        for item in facility_request.items
    ) or facility_request.status == 'completed'
    item_header = ['No.', 'Jenis fasilitas', 'Spesifikasi', 'Jml.', 'Keperluan', 'Status', 'Aset/serial']
    widths = [0.65, 3.1, 3.4, 0.8, 3.6, 2.0, 4.95]
    if include_realization:
        item_header.append('Realisasi/kondisi')
        widths = [0.65, 2.3, 2.4, 0.75, 2.3, 1.6, 2.7, 5.8]
    rows = [[rawp(safe(label), 'FormTableHeader') for label in item_header]]
    for index, item in enumerate(facility_request.items, 1):
        existing_serial = item.item_detail.serial_number if item.item_detail else item.serial_number
        row = [
            str(index), p(item.facility_name), p(item.specification), str(item.quantity), p(item.purpose),
            rawp(
                f'{checkbox(item.need_status == "new")} Baru<br/>'
                f'{checkbox(item.need_status != "new")} Eksisting'
            ),
            p(existing_serial),
        ]
        if include_realization:
            condition = {'good': 'Baik', 'damaged': 'Rusak'}.get(item.handover_condition, '-')
            row.append(p(
                f'Merek/Tipe: {item.brand_type or "-"}\nNo. inventaris: {item.inventory_number or "-"}\n'
                f'Serial: {item.serial_number or existing_serial or "-"}\nKondisi: {condition}\nCatatan: {item.handover_notes or "-"}'
            ))
        rows.append(row)
    while len(rows) < 7:
        blank_row = [
            str(len(rows)), '', '', '', '', rawp(f'{checkbox(False)} Baru<br/>{checkbox(False)} Eksisting'), '',
        ]
        if include_realization:
            blank_row.append('')
        rows.append(blank_row)
    items_table = Table(rows, colWidths=[value * cm for value in widths], repeatRows=1)
    items_table.setStyle(grid_style(header=True))
    items_table.setStyle(TableStyle([
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Paragraph(
        'Contoh fasilitas: laptop/desktop, monitor, keyboard/mouse, headset, meja/kursi, loker, kartu akses, '
        'akun SSO/email, VPN, perangkat jaringan, lisensi perangkat lunak, dan fasilitas kerja lainnya.',
        styles['FormNote'],
    ))

    story.append(section('D. ALASAN / JUSTIFIKASI KEBUTUHAN'))
    justification_table = Table([
        [[
            rawp('<b>Uraian kebutuhan dan keterkaitannya dengan pelaksanaan tugas:</b>'),
            Spacer(1, 0.08 * cm),
            p(facility_request.justification),
        ]],
        [[
            rawp('<b>Dampak apabila fasilitas tidak tersedia / dasar penggantian atau perbaikan:</b>'),
            Spacer(1, 0.08 * cm),
            p(facility_request.impact_if_unavailable),
        ]],
    ], colWidths=[content_width])
    justification_table.setStyle(grid_style())
    justification_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.extend([justification_table, PageBreak()])

    story.append(section('E. VERIFIKASI KETERSEDIAAN DAN REKOMENDASI'))
    verification = facility_request.verification
    choice_labels = {
        'available': 'Tersedia',
        'unavailable': 'Tidak tersedia',
        'procurement_required': 'Perlu pengadaan',
        'new': 'Baru',
        'good': 'Baik',
        'repair_required': 'Perlu perbaikan',
        'not_applicable': 'Tidak berlaku',
        'stock': 'Stok',
        'mutation': 'Mutasi',
        'procurement': 'Pengadaan',
        'approved': 'Disetujui',
        'partially_approved': 'Disetujui sebagian',
        'postponed': 'Ditunda',
        'rejected': 'Ditolak',
        'normal': 'Normal',
        'important': 'Penting',
        'urgent': 'Mendesak',
    }
    verification_rows = [
        [
            rawp('<b>Hasil verifikasi</b>'),
            p(choice_labels.get(verification.availability, verification.availability) if verification else 'Belum diverifikasi'),
            rawp('<b>Sumber fasilitas</b>'),
            p(choice_labels.get(verification.facility_source, verification.facility_source) if verification else '-'),
        ],
        [
            rawp('<b>Kondisi perangkat</b>'),
            p(choice_labels.get(verification.device_condition, verification.device_condition) if verification else '-'),
            rawp('<b>Estimasi penyelesaian</b>'),
            p(verification.estimated_completion.strftime('%d/%m/%Y') if verification and verification.estimated_completion else '-'),
        ],
        [
            rawp('<b>Rekomendasi</b>'),
            p(choice_labels.get(verification.recommendation, verification.recommendation) if verification else '-'),
            rawp('<b>Prioritas realisasi</b>'),
            p(choice_labels.get(verification.realization_priority, verification.realization_priority) if verification else '-'),
        ],
        [
            rawp('<b>Petugas verifikasi</b>'),
            p(verification.verifier.name if verification and verification.verifier else '-'),
            rawp('<b>Tanggal verifikasi</b>'),
            p(verification.verified_at.strftime('%d/%m/%Y %H:%M') if verification else '-'),
        ],
        [rawp('<b>Catatan verifikasi</b>'), p(verification.notes if verification else '-'), '', ''],
    ]
    verification_table = Table(verification_rows, colWidths=[3.45 * cm, 5.8 * cm, 3.45 * cm, 5.8 * cm])
    verification_table.setStyle(grid_style())
    verification_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), light_green),
        ('BACKGROUND', (2, 0), (2, 3), light_green),
        ('SPAN', (1, 4), (3, 4)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(verification_table)

    story.append(section('F. PERSETUJUAN'))
    approval_headers = [
        rawp('<b>Pemohon/Atasan Langsung</b>', 'FormCenter'),
        rawp('<b>Administrasi</b>', 'FormCenter'),
        rawp('<b>Pimpinan/Pejabat Berwenang</b>', 'FormCenter'),
    ]
    approval_cells = []
    for stage in ('unit_supervisor', 'administration', 'leadership'):
        approval = facility_request.approval_for(stage)
        if approval:
            cell = [
                rawp(f'<b>Nama:</b> {safe(approval.signer_name_snapshot)}'),
                Spacer(1, 0.04 * cm),
                rawp('<b>Tanda tangan:</b>'),
                Image(BytesIO(approval.signature_data), width=4.3 * cm, height=1.35 * cm),
                rawp(f'<b>Tanggal:</b> {approval.signed_at.strftime("%d/%m/%Y %H:%M")}'),
                p(f'Hash: {approval.document_hash[:12]}...', 'FormNote'),
            ]
        else:
            cell = [
                rawp('<b>Nama:</b> -'),
                Spacer(1, 0.12 * cm),
                rawp('<b>Tanda tangan:</b>'),
                Spacer(1, 1.35 * cm),
                rawp('<b>Tanggal:</b> -'),
                p('Belum ditandatangani', 'FormNote'),
            ]
        approval_cells.append(cell)
    approval_table = Table([approval_headers, approval_cells], colWidths=[content_width / 3] * 3)
    approval_table.setStyle(grid_style())
    approval_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_green),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 5),
    ]))
    story.append(approval_table)

    story.append(section('G. SERAH-TERIMA / PENGEMBALIAN FASILITAS'))
    if facility_request.request_type == 'return':
        from_name = facility_request.submitter_name_snapshot
        to_name = facility_request.warehouse_receiver.name if facility_request.warehouse_receiver else '-'
        from_role = 'Unit'
        to_role = 'Administrasi/Warehouse'
        handover_date = facility_request.warehouse_received_at
        action_label = 'Pengembalian fasilitas dari Unit kepada Administrasi/Warehouse'
    else:
        from_name = facility_request.releaser.name if facility_request.releaser else '-'
        to_name = facility_request.receiver.name if facility_request.receiver else '-'
        from_role = 'Administrasi/Warehouse'
        to_role = 'Unit'
        handover_date = facility_request.received_at or facility_request.released_at
        action_label = 'Penyerahan fasilitas kepada Unit'
    handover_summary = Table([
        [rawp('<b>Proses</b>'), p(action_label), rawp('<b>Status</b>'), p(facility_request.status_display)],
        [rawp('<b>Catatan</b>'), p(facility_request.receipt_notes or facility_request.operational_notes), '', ''],
    ], colWidths=[2.5 * cm, 6.75 * cm, 2.5 * cm, 6.75 * cm])
    handover_summary.setStyle(grid_style())
    handover_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), light_green),
        ('BACKGROUND', (2, 0), (2, 0), light_green),
        ('SPAN', (1, 1), (3, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(handover_summary)

    actor_date = handover_date.strftime('%d/%m/%Y %H:%M') if handover_date else '-'
    handover_table = Table([
        [rawp('<b>Diserahkan oleh</b>', 'FormCenter'), rawp('<b>Diterima oleh</b>', 'FormCenter')],
        [
            [rawp(f'<b>Nama:</b> {safe(from_name)}'), rawp(f'<b>Peran:</b> {safe(from_role)}'), rawp(f'<b>Tanggal:</b> {actor_date}')],
            [rawp(f'<b>Nama:</b> {safe(to_name)}'), rawp(f'<b>Peran:</b> {safe(to_role)}'), rawp(f'<b>Tanggal:</b> {actor_date}')],
        ],
    ], colWidths=[content_width / 2] * 2)
    handover_table.setStyle(grid_style())
    handover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_green),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
    ]))
    story.append(handover_table)
    story.append(p(
        'Serah-terima dikonfirmasi melalui akun terautentikasi, password, waktu, alamat IP, dan audit sistem; '
        'tidak menggunakan tanda tangan formal tambahan.',
        'FormNote',
    ))
    if facility_request.warehouse_received_at and facility_request.request_type in ('repair_service', 'replacement'):
        story.append(p(
            f'Aset eksisting diterima Administrasi/Warehouse oleh '
            f'{facility_request.warehouse_receiver.name if facility_request.warehouse_receiver else "-"} '
            f'pada {facility_request.warehouse_received_at.strftime("%d/%m/%Y %H:%M")}.',
        ))

    story.append(section('H. PERNYATAAN PENGGUNA'))
    if facility_request.request_type == 'return':
        statement = (
            'Unit menyatakan fasilitas telah diserahkan kembali kepada DITSINTEK USU dalam kondisi yang telah diperiksa. '
            'Konfirmasi dilakukan menggunakan akun terautentikasi dan tercatat pada audit sistem.'
        )
    else:
        statement = (
            'Unit menyatakan telah menerima fasilitas dalam kondisi yang telah diperiksa. Fasilitas akan digunakan untuk '
            'kepentingan kedinasan, dijaga keamanannya, tidak dipindahtangankan tanpa persetujuan, dan dikembalikan ketika tidak lagi digunakan.'
        )
    statement_status = 'DISETUJUI' if facility_request.user_statement_accepted or facility_request.request_type == 'return' and facility_request.status == 'completed' else 'BELUM DIKONFIRMASI'
    statement_table = Table([[
        [p(statement), Spacer(1, 0.08 * cm), rawp(f'<b>Status pernyataan: {statement_status}</b>')]
    ]], colWidths=[content_width])
    statement_table.setStyle(grid_style())
    statement_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(statement_table)

    document.build(story, onFirstPage=draw_page_chrome, onLaterPages=draw_page_chrome)
    return buffer.getvalue()


def store_final_pdf(facility_request, actor, document_type='approved_form'):
    existing = FacilityDocument.query.filter_by(
        facility_request_id=facility_request.id,
        version=facility_request.version,
        document_type=document_type,
    ).first()
    if existing:
        return existing

    pdf_bytes = generate_pdf_bytes(facility_request)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    document = FacilityDocument(
        facility_request_id=facility_request.id,
        version=facility_request.version,
        document_type=document_type,
        filename=(
            f'{facility_request.form_number}.pdf'
            if document_type == 'approved_form'
            else f'{facility_request.form_number}-{document_type}.pdf'
        ),
        mime_type='application/pdf',
        file_size=len(pdf_bytes),
        sha256=digest,
        file_data=pdf_bytes,
        is_final=True,
        created_by=actor.id,
    )
    db.session.add(document)
    db.session.flush()
    return document
