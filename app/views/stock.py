from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockTransaction, Item, Warehouse, Distribution, ReturnItem
from app.forms import StockForm, StockTransactionForm
from app.utils.decorators import role_required, warehouse_access_required
from sqlalchemy import func, and_
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable
from reportlab.pdfbase import pdfdoc
import io

bp = Blueprint('stock', __name__, url_prefix='/stock')


@bp.route('/')
@login_required
@role_required('admin')
def index():
    """Stock history page - only warehouse stock transactions"""
    # Get filter parameters
    selected_year = request.args.get('year', datetime.now().year, type=int)
    selected_month = request.args.get('month', None, type=int)

    # Unified list of all transactions (individual items)
    all_entries = []

    # Helper function to get timestamp for sorting
    def get_timestamp(entry):
        return entry.get('timestamp')

    # Build common filters for year and month
    year_filter = func.extract('year', StockTransaction.transaction_date) == selected_year
    month_filter = func.extract('month', StockTransaction.transaction_date) == selected_month if selected_month else True

    # 1. StockTransaction IN (bukan dari procurement)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            trans_in = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'IN',
                ~StockTransaction.note.like('%Procurement%'),
                ~StockTransaction.note.like('%Pengadaan%'),
                year_filter,
                month_filter
            ).order_by(StockTransaction.transaction_date.desc()).all()
        else:
            trans_in = []
    else:
        trans_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            ~StockTransaction.note.like('%Procurement%'),
            ~StockTransaction.note.like('%Pengadaan%'),
            year_filter,
            month_filter
        ).order_by(StockTransaction.transaction_date.desc()).all()

    for trans in trans_in:
        all_entries.append({
            'type': 'stock_in',
            'timestamp': trans.transaction_date,
            'data': trans
        })

    # 2. StockTransaction OUT (bukan dari procurement)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            trans_out = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'OUT',
                ~StockTransaction.note.like('%Procurement%'),
                ~StockTransaction.note.like('%Pengadaan%'),
                year_filter,
                month_filter
            ).order_by(StockTransaction.transaction_date.desc()).all()
        else:
            trans_out = []
    else:
        trans_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            ~StockTransaction.note.like('%Procurement%'),
            ~StockTransaction.note.like('%Pengadaan%'),
            year_filter,
            month_filter
        ).order_by(StockTransaction.transaction_date.desc()).all()

    for trans in trans_out:
        all_entries.append({
            'type': 'stock_out',
            'timestamp': trans.transaction_date,
            'data': trans
        })

    # 3. ReturnBatch - per item
    from app.models.return_batch import ReturnBatch

    # Build filters for return batches
    return_year_filter = func.extract('year', ReturnBatch.confirmed_at) == selected_year if selected_year else True
    return_month_filter = func.extract('month', ReturnBatch.confirmed_at) == selected_month if selected_month else True

    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            return_batches = ReturnBatch.query.filter(
                ReturnBatch.warehouse_id.in_(user_warehouse_ids),
                ReturnBatch.status == 'confirmed',
                return_year_filter,
                return_month_filter
            ).order_by(ReturnBatch.confirmed_at.desc()).all()
        else:
            return_batches = []
    else:
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            return_year_filter,
            return_month_filter
        ).order_by(ReturnBatch.confirmed_at.desc()).all()

    for batch in return_batches:
        timestamp = batch.confirmed_at if batch.confirmed_at else batch.created_at
        for item in batch.return_items:
            all_entries.append({
                'type': 'return_batch',
                'timestamp': timestamp,
                'data': (batch, item)
            })

    # 4. Procurement - per item
    from app.models.procurement import Procurement

    # Build filters for procurements
    proc_year_filter = func.extract('year', Procurement.completion_date) == selected_year if selected_year else True
    proc_month_filter = func.extract('month', Procurement.completion_date) == selected_month if selected_month else True

    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            procurements = Procurement.query.filter(
                Procurement.warehouse_id.in_(user_warehouse_ids),
                Procurement.status == 'completed',
                proc_year_filter,
                proc_month_filter
            ).order_by(Procurement.completion_date.desc()).all()
        else:
            procurements = []
    else:
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            proc_year_filter,
            proc_month_filter
        ).order_by(Procurement.completion_date.desc()).all()

    for proc in procurements:
        timestamp = proc.completion_date if proc.completion_date else proc.created_at
        for item in proc.items:
            all_entries.append({
                'type': 'procurement',
                'timestamp': timestamp,
                'data': (proc, item)
            })

    # 5. DistributionGroup - per item
    from app.models.distribution_group import DistributionGroup

    # Build filters for distribution groups
    dist_year_filter = func.extract('year', DistributionGroup.verified_at) == selected_year if selected_year else True
    dist_month_filter = func.extract('month', DistributionGroup.verified_at) == selected_month if selected_month else True

    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            distribution_groups = DistributionGroup.query.filter(
                DistributionGroup.warehouse_id.in_(user_warehouse_ids),
                DistributionGroup.status.in_(['approved', 'distributed']),
                dist_year_filter,
                dist_month_filter
            ).order_by(DistributionGroup.verified_at.desc()).all()
        else:
            distribution_groups = []
    else:
        distribution_groups = DistributionGroup.query.filter(
            DistributionGroup.status.in_(['approved', 'distributed']),
            dist_year_filter,
            dist_month_filter
        ).order_by(DistributionGroup.verified_at.desc()).all()

    for group in distribution_groups:
        timestamp = group.verified_at if group.verified_at else group.created_at
        for dist in group.distributions:
            all_entries.append({
                'type': 'distribution_group',
                'timestamp': timestamp,
                'data': (group, dist)
            })

    # 6. Direct Distribution - per item
    # Build filters for direct distributions
    direct_dist_year_filter = func.extract('year', Distribution.created_at) == selected_year if selected_year else True
    direct_dist_month_filter = func.extract('month', Distribution.created_at) == selected_month if selected_month else True

    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            direct_distributions = Distribution.query.filter(
                Distribution.warehouse_id.in_(user_warehouse_ids),
                Distribution.distribution_group_id == None,
                Distribution.status == 'installed',
                direct_dist_year_filter,
                direct_dist_month_filter
            ).order_by(Distribution.created_at.desc()).all()
        else:
            direct_distributions = []
    else:
        direct_distributions = Distribution.query.filter(
            Distribution.distribution_group_id == None,
            Distribution.status == 'installed',
            direct_dist_year_filter,
            direct_dist_month_filter
        ).order_by(Distribution.created_at.desc()).all()

    for dist in direct_distributions:
        all_entries.append({
            'type': 'direct_distribution',
            'timestamp': dist.created_at,
            'data': dist
        })

    # Sort all entries by timestamp (newest first)
    all_entries.sort(key=get_timestamp, reverse=True)

    # Get available years and months for filter dropdown
    from sqlalchemy import distinct
    available_years = db.session.query(
        distinct(func.extract('year', StockTransaction.transaction_date))
    ).order_by(func.extract('year', StockTransaction.transaction_date).desc()).all()

    available_years = [int(y[0]) for y in available_years if y[0]]

    return render_template('stock/index.html',
                         all_entries=all_entries,
                         selected_year=selected_year,
                         selected_month=selected_month,
                         available_years=available_years)


@bp.route('/recap')
@login_required
@role_required('admin')
def recap():
    """Annual recap/report page"""
    year = request.args.get('year', datetime.now().year, type=int)

    # Get stock transactions per month (exclude procurement to avoid duplication)
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            stock_in = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'IN',
                ~StockTransaction.note.like('%Pengadaan%'),
                func.extract('year', StockTransaction.transaction_date) == year
            ).all()
            stock_out = StockTransaction.query.filter(
                StockTransaction.warehouse_id.in_(user_warehouse_ids),
                StockTransaction.transaction_type == 'OUT',
                func.extract('year', StockTransaction.transaction_date) == year
            ).all()
        else:
            stock_in = []
            stock_out = []
    else:
        stock_in = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'IN',
            ~StockTransaction.note.like('%Pengadaan%'),
            func.extract('year', StockTransaction.transaction_date) == year
        ).all()
        stock_out = StockTransaction.query.filter(
            StockTransaction.transaction_type == 'OUT',
            func.extract('year', StockTransaction.transaction_date) == year
        ).all()

    # Get distributions to units
    distributions = Distribution.query.filter(
        func.extract('year', Distribution.created_at) == year
    ).all()

    # Get returns from units
    returns = ReturnItem.query.filter(
        func.extract('year', ReturnItem.created_at) == year,
        ReturnItem.status == 'returned'
    ).all()

    # Calculate totals
    total_in = sum(t.quantity for t in stock_in)
    # Total out = stock transactions OUT + distributions to units
    total_out = sum(t.quantity for t in stock_out) + len(distributions)
    total_distributed = len(distributions)
    total_returned = len(returns)

    # Group by source/destination
    in_by_source = {}
    for t in stock_in:
        source = t.warehouse.name if t.warehouse else 'Unknown'
        in_by_source[source] = in_by_source.get(source, 0) + t.quantity

    # Group stock out by warehouse
    out_by_source = {}
    for t in stock_out:
        source = t.warehouse.name if t.warehouse else 'Unknown'
        out_by_source[source] = out_by_source.get(source, 0) + t.quantity

    # Add distributions to out_by_source (group by warehouse name)
    for d in distributions:
        source = d.warehouse.name if d.warehouse else 'Unknown'
        out_by_source[source] = out_by_source.get(source, 0) + 1

    # Obname: items still in warehouse (status: available) created in selected year
    from app.models.master_data import ItemDetail
    obname_items = ItemDetail.query.filter(
        ItemDetail.status == 'available',
        func.extract('year', ItemDetail.created_at) == year
    ).all()
    total_obname = len(obname_items)

    # Get procurements (completed in selected year)
    from app.models.procurement import Procurement
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            procurements = Procurement.query.filter(
                Procurement.warehouse_id.in_(user_warehouse_ids),
                Procurement.status == 'completed',
                func.extract('year', Procurement.completion_date) == year
            ).all()
        else:
            procurements = []
    else:
        procurements = Procurement.query.filter(
            Procurement.status == 'completed',
            func.extract('year', Procurement.completion_date) == year
        ).all()

    # Calculate procurement total
    total_procurement = sum(item.quantity for proc in procurements for item in proc.items)

    # Get return batches (confirmed in selected year)
    from app.models.return_batch import ReturnBatch
    if current_user.is_warehouse_staff():
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            return_batches = ReturnBatch.query.filter(
                ReturnBatch.warehouse_id.in_(user_warehouse_ids),
                ReturnBatch.status == 'confirmed',
                func.extract('year', ReturnBatch.confirmed_at) == year
            ).all()
        else:
            return_batches = []
    else:
        return_batches = ReturnBatch.query.filter(
            ReturnBatch.status == 'confirmed',
            func.extract('year', ReturnBatch.confirmed_at) == year
        ).all()

    # Calculate return batch total
    total_return_batches = sum(len(batch.return_items) for batch in return_batches)

    # Calculate perolehan (total procured items)
    total_perolehan = total_procurement

    return render_template('stock/recap.html',
                         year=year,
                         now=datetime.now(),
                         total_in=total_in,
                         total_out=total_out,
                         total_distributed=total_distributed,
                         total_returned=total_returned,
                         total_obname=total_obname,
                         total_procurement=total_procurement,
                         total_return_batches=total_return_batches,
                         total_perolehan=total_perolehan,
                         in_by_source=in_by_source,
                         out_by_source=out_by_source,
                         stock_in=stock_in,
                         stock_out=stock_out,
                         distributions=distributions,
                         returns=returns,
                         obname_items=obname_items,
                         procurements=procurements,
                         return_batches=return_batches)


@bp.route('/recap/pdf')
@login_required
@role_required('admin')
def recap_pdf():
    """Generate professional PDF report using ReportLab with footer"""
    # Verify user is authenticated
    if not current_user or not current_user.is_authenticated:
        flash('Anda harus login untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('auth.login'))

    # Verify user is admin
    if not current_user.is_admin():
        flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
        return redirect(url_for('dashboard.index'))

    from app.models.procurement import Procurement
    from app.models.master_data import ItemDetail
    from app.models.return_batch import ReturnBatch
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, Frame, PageTemplate
    )
    from reportlab.pdfgen import canvas
    import io
    from datetime import datetime

    year = request.args.get('year', datetime.now().year, type=int)
    now = datetime.now()

    # Get data (admin only - no warehouse filter needed)
    procurements = Procurement.query.filter(
        Procurement.status == 'completed',
        func.extract('year', Procurement.completion_date) == year
    ).all()
    stock_out = StockTransaction.query.filter(
        StockTransaction.transaction_type == 'OUT',
        func.extract('year', StockTransaction.transaction_date) == year
    ).all()
    distributions = Distribution.query.filter(
        func.extract('year', Distribution.created_at) == year
    ).all()
    return_batches = ReturnBatch.query.filter(
        ReturnBatch.status == 'confirmed',
        func.extract('year', ReturnBatch.confirmed_at) == year
    ).all()
    obname_items = ItemDetail.query.filter(
        ItemDetail.status == 'available'
    ).all()

    # Calculate totals
    total_procurement = sum(item.quantity for proc in procurements for item in proc.items)
    total_out = sum(t.quantity for t in stock_out)
    total_distributed = len(distributions)
    total_returned = sum(len(batch.return_items) for batch in return_batches)
    total_obname = len(obname_items)

    # Custom Canvas with Footer
    class FooterCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self.pages = []

        def showPage(self):
            self.pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self.pages)
            for page_num, page in enumerate(self.pages, 1):
                self.__dict__.update(page)
                self.draw_footer(page_num, page_count)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_footer(self, page_num, page_count):
            # Garis horizontal
            self.setStrokeColor(colors.HexColor('#059669'))
            self.setLineWidth(1)
            self.line(1*cm, 1*cm, landscape(A4)[0] - 1*cm, 1*cm)
            
            # Teks footer
            self.setFont('Helvetica', 8)
            self.setFillColor(colors.grey)
            
            # Tanggal dan jam cetak (kiri)
            footer_left = f"Dicetak pada: {now.strftime('%d %B %Y, %H:%M')} WIB"
            self.drawString(1*cm, 0.6*cm, footer_left)
            
            # Nomor halaman (kanan)
            footer_right = f"Halaman {page_num} dari {page_count}"
            self.drawRightString(landscape(A4)[0] - 1*cm, 0.6*cm, footer_right)

    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.8*cm  # Lebih besar untuk footer
    )

    # --- OPTIMASI STYLES (Mengurangi Spacing) ---
    title_style = ParagraphStyle(
        'CustomTitle',
        fontSize=20, # Ukuran dikecilkan sedikit agar lebih proporsional
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=10, # Dikurangi dari 20
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        fontSize=11,
        alignment=1,
        spaceAfter=15, # Dikurangi dari 30
        textColor=colors.HexColor('#64748b')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor('#059669'),
        alignment=0, # Rata kiri lebih profesional untuk section
        spaceAfter=8,
        spaceBefore=12,
        leftIndent=5,
        borderPadding=5
    )

    content = []

 # ========== 1. LETTERHEAD (COMPACT) ==========
    letterhead_data = [[
        Paragraph('<font size=20 color="white"><b>G</b></font>', 
                  ParagraphStyle('Logo', alignment=1, leading=22)),
        Paragraph(
            '<b><font size=13>LOKASET</font></b><br/>'
            '<font size=8 color="#64748b">Universitas Sumatera Utara, Jl. Universitas No.9, Padang Bulan, Medan Baru, Medan City, North Sumatra 20155 | Telp: (061) 8222129 </font>',
            ParagraphStyle('LH', leading=11, leftIndent=5)
        )
    ]]
    # Lebar total 27.7cm
    letterhead_table = Table(letterhead_data, colWidths=[1.5*cm, 26.2*cm])
    letterhead_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#059669')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (1, 0), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    content.append(letterhead_table)
    content.append(Spacer(1, 0.4*cm)) # Spacing kecil setelah header

    # ========== 2. JUDUL ==========
    content.append(Paragraph("LAPORAN REKAPITULASI TAHUNAN", title_style))
    content.append(Paragraph(f"Tahun Anggaran {year} • Dicetak: {now.strftime('%d/%m/%Y %H:%M')}", subtitle_style))

    # ========== 3. SUMMARY CARDS (HORIZONTAL FLOW) ==========
    def make_card(label, value, color):
        return Paragraph(
            f'<para align="center"><font size=8 color="#64748b">{label}</font><br/>'
            f'<b><font size=14 color="{color}">{value}</font></b></para>',
            ParagraphStyle('CardInner', leading=16)
        )

    summary_data = [[
        make_card("TOTAL PENGADAAN", f"{total_procurement:,}", "#059669"),
        make_card("TOTAL DISTRIBUSI", f"{total_distributed:,}", "#dc2626"),
        make_card("TOTAL RETUR", f"{total_returned:,}", "#ea580c"),
        make_card("SISA GUDANG", f"{total_obname:,}", "#2563eb")
    ]]
    
    # 27.7 / 4 = 6.9cm per card
    summary_table = Table(summary_data, colWidths=[6.9*cm]*4)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fef2f2')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#fff7ed')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#eff6ff')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 0.5*cm))

    # ========== SECTION I: PROCUREMENT ==========
    if procurements:
        content.append(Paragraph("I. PEROLEHAN BARANG (PENGADAAN)", heading_style))
        content.append(Spacer(1, 0.3*cm))

        # Define styles for wrapping text
        normal_text_style = ParagraphStyle('NormalText', fontSize=7, leading=9, alignment=1)  # Center-aligned for wrapping

        proc_data = [['No', 'Tanggal', 'No. Pengadaan', 'Nama Barang', 'Qty', 'Gudang', 'Supplier']]

        item_no = 1
        for proc in procurements:
            for item in proc.items:
                item_name = item.item.name if item.item else '-'
                item_code = f"Kode: {item.item.item_code if item.item else ''}"

                proc_data.append([
                    str(item_no),
                    proc.completion_date.strftime('%d/%m/%Y') if proc.completion_date else proc.created_at.strftime('%d/%m/%Y'),
                    f"PR-{proc.id}",
                    Paragraph(f"{item_name}<br/><font size=6 color='#666'>{item_code}</font>", ParagraphStyle('ItemName', fontSize=7, leading=9)),
                    str(item.quantity),
                    Paragraph(proc.warehouse.name if proc.warehouse else '-', normal_text_style),
                    Paragraph(proc.supplier.name if proc.supplier else '-', normal_text_style)
                ])
                item_no += 1

        proc_data.append([
            '', '', '',
            Paragraph('TOTAL PENGADAAN', ParagraphStyle('tot', fontSize=8, alignment=1, fontName='Helvetica-Bold')),
            str(total_procurement), '', ''
        ])

        proc_table = Table(
            proc_data,
            colWidths=[0.8*cm, 2.5*cm, 2.2*cm, 9*cm, 1.2*cm, 3.5*cm, 3.5*cm],
            repeatRows=1
        )
        proc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#059669')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#059669')),
        ]))
        content.append(proc_table)

    # ========== SECTION II: STOCK OUT & DISTRIBUTIONS ==========
    if stock_out or distributions:
        content.append(PageBreak())
        content.append(Paragraph("II. BARANG KELUAR", heading_style))
        content.append(Spacer(1, 0.3*cm))

        # Define styles for wrapping text
        normal_text_style = ParagraphStyle('NormalText', fontSize=7, leading=9, alignment=1)

        out_data = [['No', 'Tanggal', 'Nama Barang', 'Gudang Asal', 'Tujuan', 'Qty', 'Keterangan']]
        item_no = 1

        for trans in stock_out:
            item_info = f"{trans.item.name}<br/><font size=6 color='#666'>Kode: {trans.item.item_code}</font>"
            out_data.append([
                str(item_no),
                trans.transaction_date.strftime('%d/%m/%Y'),
                Paragraph(item_info, ParagraphStyle('ItemName', fontSize=7, leading=9)),
                Paragraph(trans.warehouse.name if trans.warehouse else '-', normal_text_style),
                Paragraph('-', normal_text_style),
                str(trans.quantity),
                Paragraph(trans.note or 'Pengeluaran barang', ParagraphStyle('Note', fontSize=7, leading=9, alignment=0))
            ])
            item_no += 1

        for dist in distributions:
            item_info = f"{dist.item_detail.item.name if dist.item_detail and dist.item_detail.item else '-'}"
            item_code = f"Kode: {dist.item_detail.item.item_code if dist.item_detail and dist.item_detail.item else ''}<br/>SN: {dist.item_detail.serial_number if dist.item_detail else ''}"

            out_data.append([
                str(item_no),
                dist.created_at.strftime('%d/%m/%Y'),
                Paragraph(f"{item_info}<br/><font size=6 color='#666'>{item_code}</font>", ParagraphStyle('ItemName', fontSize=7, leading=9)),
                Paragraph(dist.warehouse.name if dist.warehouse else '-', normal_text_style),
                Paragraph(dist.unit.name if dist.unit else '-', normal_text_style),
                '1',
                Paragraph('Distribusi ke unit', ParagraphStyle('Note', fontSize=7, leading=9, alignment=0))
            ])
            item_no += 1

        out_data.append([
            '', '', '', '',
            Paragraph('TOTAL KELUAR', ParagraphStyle('tot', fontSize=8, alignment=1, fontName='Helvetica-Bold')),
            str(total_out + total_distributed), ''
        ])

        out_table = Table(
            out_data,
            colWidths=[0.8*cm, 2.5*cm, 8*cm, 3.5*cm, 3*cm, 1.2*cm, 4.7*cm],
            repeatRows=1
        )
        out_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0369a1')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#0369a1')),
        ]))
        content.append(out_table)

    # ========== SECTION III: RETURNS ==========
    if return_batches:
        content.append(PageBreak())
        content.append(Paragraph("III. RETUR DARI UNIT", heading_style))
        content.append(Spacer(1, 0.3*cm))

        # Define styles for wrapping text
        normal_text_style = ParagraphStyle('NormalText', fontSize=7, leading=9, alignment=1)

        ret_data = [['No', 'Tanggal', 'No. Batch', 'Nama Barang', 'Serial Number', 'Unit Asal', 'Gudang']]
        item_no = 1

        for batch in return_batches:
            for item in batch.return_items:
                item_info = f"{item.item_detail.item.name if item.item_detail and item.item_detail.item else '-'}"
                item_code = f"Kode: {item.item_detail.item.item_code if item.item_detail and item.item_detail.item else ''}"

                ret_data.append([
                    str(item_no),
                    batch.confirmed_at.strftime('%d/%m/%Y') if batch.confirmed_at else batch.created_at.strftime('%d/%m/%Y'),
                    Paragraph(batch.batch_code, ParagraphStyle('BatchCode', fontSize=6, leading=8, alignment=1)),
                    Paragraph(f"{item_info}<br/><font size=6 color='#666'>{item_code}</font>", ParagraphStyle('ItemName', fontSize=7, leading=9)),
                    item.item_detail.serial_unit if item.item_detail else '',
                    Paragraph(item.unit.name if item.unit else '-', normal_text_style),
                    Paragraph(batch.warehouse.name if batch.warehouse else '-', normal_text_style)
                ])
                item_no += 1

        ret_data.append([
            '', '', '', '', '',
            Paragraph('TOTAL RETUR', ParagraphStyle('tot', fontSize=8, alignment=1, fontName='Helvetica-Bold')),
            str(total_returned)
        ])

        ret_table = Table(
            ret_data,
            colWidths=[0.8*cm, 2.5*cm, 3.5*cm, 7*cm, 2.5*cm, 3*cm, 4.4*cm],
            repeatRows=1
        )
        ret_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#a16207')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#a16207')),
        ]))
        content.append(ret_table)

    # ========== SECTION IV: STOCK OPNAME ==========
    if obname_items:
        content.append(PageBreak())
        content.append(Paragraph("IV. DAFTAR BARANG DI GUDANG (STOCK OPNAME)", heading_style))
        content.append(Spacer(1, 0.3*cm))

        # Define styles for wrapping text
        normal_text_style = ParagraphStyle('NormalText', fontSize=7, leading=9, alignment=1)

        stock_data = [['No', 'Nama Barang', 'Serial Number', 'Gudang', 'Tanggal Masuk', 'Status']]

        for idx, item in enumerate(obname_items, 1):
            item_info = f"{item.item.name}"
            item_code = f"Kode: {item.item.item_code}"

            stock_data.append([
                str(idx),
                Paragraph(f"{item_info}<br/><font size=6 color='#666'>{item_code}</font>", ParagraphStyle('ItemName', fontSize=7, leading=9)),
                item.serial_number,
                Paragraph(item.warehouse.name if item.warehouse else '-', normal_text_style),
                item.created_at.strftime('%d/%m/%Y'),
                '✓ Tersedia'
            ])

        stock_data.append([
            '', '', '', '',
            Paragraph('TOTAL BARANG', ParagraphStyle('tot', fontSize=8, alignment=1, fontName='Helvetica-Bold')),
            str(total_obname)
        ])

        stock_table = Table(
            stock_data,
            colWidths=[0.8*cm, 8*cm, 3*cm, 3.5*cm, 2.8*cm, 4.6*cm],
            repeatRows=1
        )
        stock_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ede9fe')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#6b21a8')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#6b21a8')),
        ]))
        content.append(stock_table)

    # ========== SIGNATURE SECTION ==========
    content.append(PageBreak())
    content.append(Paragraph("PENGESAHAN LAPORAN", heading_style))
    content.append(Spacer(1, 0.5*cm))

    sig_text = (
        f"Demikian laporan rekapitulasi barang masuk dan keluar untuk tahun anggaran {year} "
        f"ini dibuat dengan sebenar-benarnya berdasarkan data yang ada dalam sistem. "
        f"Laporan ini dapat digunakan sebagai bahan evaluasi dan perencanaan untuk periode selanjutnya."
    )
    content.append(Paragraph(
        sig_text, 
        ParagraphStyle('BodyText', fontSize=10, alignment=4, leading=14)
    ))
    content.append(Spacer(1, 1.5*cm))

    sig_data = [
        ['Mengetahui,', '', 'Kepala Gudang,'],
        [f'{now.strftime("%d %B %Y")}', '', f'{now.strftime("%d %B %Y")}'],
        ['', '', ''],
        ['', '', ''],
        ['', '', ''],
        ['( .............................. )', '', '( .............................. )'],
        ['Kepala Divisi Logistik', '', 'Kepala Gudang'],
        ['NIP. ..............................', '', 'NIP. ..............................'],
    ]

    sig_table = Table(sig_data, colWidths=[6*cm, 4*cm, 6*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (2, 0), (2, 0), colors.HexColor('#059669')),
        ('FONTNAME', (0, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (2, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 6), (-1, 7), 9),
        ('TEXTCOLOR', (0, 6), (-1, 7), colors.grey),
    ]))
    content.append(sig_table)
    content.append(Spacer(1, 1*cm))

    # ========== NOTE SECTION ==========
    note_content = [
        [Paragraph(
            "<b>Catatan Penting:</b>",
            ParagraphStyle('NoteTitle', fontSize=10, textColor=colors.HexColor('#059669'), fontName='Helvetica-Bold')
        )],
        [Paragraph(
            "Laporan ini bersifat rahasia dan hanya untuk keperluan internal. "
            "Mohon untuk tidak menyebarluaskan tanpa izin dari pihak yang berwenang. "
            "Segala kesalahan dalam laporan ini merupakan tanggung jawab penyusun "
            "dan dapat dikoreksi berdasarkan data yang valid.",
            ParagraphStyle('NoteBody', fontSize=9, textColor=colors.HexColor('#065f46'), leading=12)
        )]
    ]

    note_table = Table(note_content, colWidths=[26*cm])
    note_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#d1fae5')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#059669')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(note_table)

    # ========== SET PDF METADATA ==========
    doc.title = f'Laporan Rekap Tahunan - {year}'
    doc.author = f'{current_user.name} ({current_user.email})'
    doc.subject = f'Laporan Rekap Stok Tahun {year}'
    doc.creator = 'Smart Geo Inventory System'

    # ========== BUILD PDF ==========
    doc.build(content, canvasmaker=FooterCanvas)

    # Get PDF value
    pdf = buffer.getvalue()
    buffer.close()

    # Create response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Laporan_Rekap_Tahunan_{year}.pdf'

    return response


@bp.route('/per-unit')
@login_required
@role_required('admin')
def per_unit():
    """Show list of all units with their stock summary"""
    from app.models import Unit
    from app.models.distribution import Distribution
    from app.models.master_data import ItemDetail

    # Get all active units
    units = Unit.query.filter_by(status='active').all()

    unit_summary = []
    for unit in units:
        # Get all distributions to this unit that are not rejected/returned
        distributions = Distribution.query.filter(
            Distribution.unit_id == unit.id,
            Distribution.status != 'rejected'
        ).all()

        # Get item details for this unit (excluding returned items)
        item_detail_ids = [d.item_detail_id for d in distributions if d.item_detail_id]

        if item_detail_ids:
            # Get item details and exclude returned ones
            item_details = ItemDetail.query.filter(
                ItemDetail.id.in_(item_detail_ids),
                ItemDetail.status != 'returned'
            ).all()

            # Count by item_detail status
            total_items = len(item_details)
            loaned_count = len([d for d in item_details if d.status == 'loaned'])
            used_count = len([d for d in item_details if d.status == 'used'])
        else:
            total_items = 0
            loaned_count = 0
            used_count = 0

        unit_summary.append({
            'unit': unit,
            'total_items': total_items,
            'loaned_count': loaned_count,
            'used_count': used_count
        })

    return render_template('stock/per_unit.html', unit_summary=unit_summary)


@bp.route('/per-unit/<int:unit_id>')
@login_required
@role_required('admin')
def per_unit_detail(unit_id):
    """Show detailed stock for a specific unit (similar to unit-assets)"""
    from app.models import Unit
    from app.models.distribution import Distribution
    from app.models.master_data import ItemDetail
    from collections import defaultdict

    # Get the unit
    unit = Unit.query.get_or_404(unit_id)

    # Get all distributions to this unit (excluding rejected)
    distributions = Distribution.query.filter(
        Distribution.unit_id == unit_id,
        Distribution.status != 'rejected'
    ).all()

    # Get all item details for this unit (excluding returned items)
    item_detail_ids = [d.item_detail_id for d in distributions if d.item_detail_id]
    item_details = ItemDetail.query.filter(
        ItemDetail.id.in_(item_detail_ids),
        ItemDetail.status != 'returned'
    ).all() if item_detail_ids else []

    # Calculate stats
    in_unit_count = len([d for d in item_details if d.status == 'in_unit'])
    loaned_count = len([d for d in item_details if d.status == 'loaned'])
    used_count = len([d for d in item_details if d.status == 'used'])

    # Group items by item_id (only include items that are not returned)
    items_dict = defaultdict(lambda: {
        'item': None,
        'details': [],
        'total_quantity': 0
    })

    # Collect all items from distributions (excluding returned items)
    for dist in distributions:
        if dist.item_detail and dist.item_detail.item and dist.item_detail.status != 'returned':
            item_id = dist.item_detail.item_id
            items_dict[item_id]['item'] = dist.item_detail.item
            items_dict[item_id]['details'].append({
                'item_detail': dist.item_detail,
                'serial_number': dist.item_detail.serial_number,
                'distribution_date': dist.installed_at or dist.created_at,
                'location': f"{dist.unit_detail.room_name if dist.unit_detail else 'N/A'}",
                'status': dist.item_detail.status,
                'distribution_id': dist.id
            })
            items_dict[item_id]['total_quantity'] += 1

    # Sort items by name
    sorted_items = sorted(items_dict.values(), key=lambda x: x['item'].name if x['item'] else '')

    return render_template('stock/per_unit_detail.html',
                         unit=unit,
                         items=sorted_items,
                         total_items=len(item_details),
                         in_unit_count=in_unit_count,
                         loaned_count=loaned_count,
                         used_count=used_count)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def add():
    """Add stock transaction (IN)"""
    form = StockTransactionForm()

    # Populate choices
    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    if current_user.is_warehouse_staff():
        # Get warehouses from UserWarehouse assignments (many-to-many)
        user_warehouses = current_user.user_warehouses.all()
        if user_warehouses:
            form.warehouse_id.choices = [(uw.warehouse.id, uw.warehouse.name) for uw in user_warehouses]
        else:
            form.warehouse_id.choices = []
    else:
        form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    if form.validate_on_submit():
        try:
            # Get or create stock record
            stock = Stock.query.filter_by(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data
            ).first()

            if not stock:
                stock = Stock(
                    item_id=form.item_id.data,
                    warehouse_id=form.warehouse_id.data,
                    quantity=0
                )

            # Add stock
            if form.transaction_type.data == 'IN':
                stock.add_stock(form.quantity.data)
            else:
                if not stock.remove_stock(form.quantity.data):
                    flash('Stok tidak mencukupi!', 'danger')
                    return render_template('stock/add.html', form=form)

            # Create transaction record
            transaction = StockTransaction(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data,
                transaction_type=form.transaction_type.data,
                quantity=form.quantity.data,
                note=form.note.data
            )
            transaction.save()

            flash('Transaksi stok berhasil!', 'success')
            return redirect(url_for('stock.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('stock/add.html', form=form, transaction_type='IN')


@bp.route('/remove', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_staff', 'admin')
def remove():
    """Remove stock transaction (OUT)"""
    form = StockTransactionForm()

    form.item_id.choices = [(i.id, f"{i.item_code} - {i.name}") for i in Item.query.all()]

    if current_user.is_warehouse_staff():
        # Get warehouses from UserWarehouse assignments (many-to-many)
        user_warehouses = current_user.user_warehouses.all()
        if user_warehouses:
            form.warehouse_id.choices = [(uw.warehouse.id, uw.warehouse.name) for uw in user_warehouses]
        else:
            form.warehouse_id.choices = []
    else:
        form.warehouse_id.choices = [(w.id, w.name) for w in Warehouse.query.all()]

    if form.validate_on_submit():
        try:
            stock = Stock.query.filter_by(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data
            ).first()

            if not stock:
                flash('Stok tidak ditemukan!', 'danger')
                return render_template('stock/remove.html', form=form)

            # Remove stock
            if not stock.remove_stock(form.quantity.data):
                flash('Stok tidak mencukupi!', 'danger')
                return render_template('stock/remove.html', form=form)

            # Create transaction record
            transaction = StockTransaction(
                item_id=form.item_id.data,
                warehouse_id=form.warehouse_id.data,
                transaction_type=form.transaction_type.data,
                quantity=form.quantity.data,
                note=form.note.data
            )
            transaction.save()

            flash('Transaksi stok berhasil!', 'success')
            return redirect(url_for('stock.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return render_template('stock/remove.html', form=form, transaction_type='OUT')


@bp.route('/low-stock')
@login_required
@role_required('admin')
def low_stock():
    """Show low stock items"""
    threshold = request.args.get('threshold', 10, type=int)
    low_stocks = Stock.query.filter(Stock.quantity < threshold).all()

    return render_template('stock/low_stock.html', low_stocks=low_stocks, threshold=threshold)


@bp.route('/transactions')
@login_required
@role_required('admin')
def transactions():
    """Show stock transaction history"""
    if current_user.is_warehouse_staff():
        # Get warehouse IDs from UserWarehouse assignments (many-to-many)
        user_warehouse_ids = [uw.warehouse_id for uw in current_user.user_warehouses.all()]
        if user_warehouse_ids:
            transactions = StockTransaction.query.filter(StockTransaction.warehouse_id.in_(user_warehouse_ids)).order_by(StockTransaction.transaction_date.desc()).all()
        else:
            transactions = []
    else:
        transactions = StockTransaction.query.order_by(StockTransaction.transaction_date.desc()).all()

    return render_template('stock/transactions.html', transactions=transactions)


@bp.route('/item/<int:item_id>')
@login_required
@role_required('admin')
def item_stock(item_id):
    """Show stock for specific item across warehouses"""
    item = Item.query.get_or_404(item_id)
    stocks = Stock.query.filter_by(item_id=item_id).all()

    return render_template('stock/item_stock.html', item=item, stocks=stocks)


