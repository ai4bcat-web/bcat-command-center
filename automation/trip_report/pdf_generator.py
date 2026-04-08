"""
automation/trip_report/pdf_generator.py
────────────────────────────────────────
PDFReportGenerator

Produces a clean, professional PDF for a single DriverReport using reportlab.

Layout
──────
  • Header bar  — company name + "Amazon Trip Report"
  • Driver card — driver name + type badge + report date + window
  • Summary row — Total Trips  |  Total Revenue
  • Trip table  — Date / Trip ID / Route / Revenue / Status
  • Footer row  — GRAND TOTAL  (trips + revenue)

Output
──────
Files are written to REPORT_OUTPUT_DIR (env var, default: /tmp/trip_reports/).
Filename pattern:  trip_report_{driver_slug}_{report_date}.pdf
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# ── colour palette (matches dark dashboard brand) ─────────────────────────────
BRAND_BLUE   = (0.055, 0.149, 0.306)   # #0e2650 — header / accent
ACCENT_LIGHT = (0.231, 0.741, 0.973)   # #3bbdf8 — revenue highlight
LIGHT_GREY   = (0.933, 0.933, 0.933)   # #eeeeee — table alt row
MID_GREY     = (0.600, 0.600, 0.600)   # #999999 — secondary text
WHITE        = (1.000, 1.000, 1.000)
BLACK        = (0.000, 0.000, 0.000)


def _output_dir() -> Path:
    d = Path(os.getenv('REPORT_OUTPUT_DIR', '/tmp/trip_reports'))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


class PDFReportGenerator:
    """Generates one PDF file per DriverReport."""

    def generate(self, report) -> str:
        """Generate a PDF and return its absolute file path.

        Args:
            report: DriverReport dataclass instance.

        Returns:
            Absolute path to the generated PDF file.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units     import inch
        from reportlab.lib           import colors
        from reportlab.platypus      import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums     import TA_CENTER, TA_LEFT, TA_RIGHT

        filename = f"trip_report_{_slug(report.driver_name)}_{report.report_date}.pdf"
        out_path = _output_dir() / filename

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize       = letter,
            leftMargin     = 0.75 * inch,
            rightMargin    = 0.75 * inch,
            topMargin      = 0.75 * inch,
            bottomMargin   = 0.75 * inch,
        )

        styles  = getSampleStyleSheet()
        story   = []

        # ── 1. Header banner ──────────────────────────────────────────────────
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent    = styles['Normal'],
            fontSize  = 10,
            textColor = colors.Color(*WHITE),
            spaceAfter= 0,
        )
        title_style = ParagraphStyle(
            'TitleStyle',
            parent    = styles['Normal'],
            fontSize  = 16,
            textColor = colors.Color(*WHITE),
            leading   = 20,
        )
        header_data = [[
            Paragraph('<b>BCAT Command Center</b>', title_style),
            Paragraph('Amazon Weekly Trip Report', header_style),
        ]]
        header_table = Table(header_data, colWidths=[4 * inch, 2.5 * inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(*BRAND_BLUE)),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('LEFTPADDING',   (0, 0), (0, 0), 16),
            ('RIGHTPADDING',  (-1, 0), (-1, 0), 16),
            ('ALIGN',         (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.25 * inch))

        # ── 2. Driver card ────────────────────────────────────────────────────
        driver_label = ParagraphStyle(
            'DriverLabel',
            parent    = styles['Normal'],
            fontSize  = 9,
            textColor = colors.Color(*MID_GREY),
            spaceAfter= 2,
        )
        driver_name_style = ParagraphStyle(
            'DriverName',
            parent    = styles['Normal'],
            fontSize  = 20,
            leading   = 24,
            textColor = colors.Color(*BRAND_BLUE),
        )
        dtype_badge = '● Company Driver' if report.driver_type == 'company' else '● Owner Operator'

        # Build "Sun Apr 5 – Sat Apr 11, 2026" style week label
        week_label = ''
        report_date_label = report.report_date
        if report.window_start and report.window_end:
            try:
                s = datetime.strptime(report.window_start, '%Y-%m-%d')
                e = datetime.strptime(report.window_end,   '%Y-%m-%d')
                week_label = (
                    f"{s.strftime('%a %b %-d')} – {e.strftime('%a %b %-d, %Y')}"
                )
                report_date_label = f"Week of {s.strftime('%-d %b')} – {e.strftime('%-d %b %Y')}"
            except ValueError:
                week_label = f"{report.window_start} – {report.window_end}"

        card_data = [
            [Paragraph('DRIVER',       driver_label), Paragraph('REPORTING WEEK', driver_label)],
            [Paragraph(f'<b>{report.driver_name}</b>', driver_name_style),
             Paragraph(report_date_label, driver_name_style)],
            [Paragraph(dtype_badge,    driver_label), Paragraph(week_label, driver_label)],
        ]
        card_table = Table(card_data, colWidths=[4.5 * inch, 2 * inch])
        card_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.Color(0.96, 0.97, 0.99)),
            ('BOX',           (0, 0), (-1, -1), 0.5, colors.Color(*LIGHT_GREY)),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
            ('TOPPADDING',    (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ]))
        story.append(card_table)
        story.append(Spacer(1, 0.2 * inch))

        # ── 3. Summary metric row ─────────────────────────────────────────────
        metric_label = ParagraphStyle(
            'MetricLabel',
            parent    = styles['Normal'],
            fontSize  = 8,
            textColor = colors.Color(*MID_GREY),
            alignment = TA_CENTER,
        )
        metric_val = ParagraphStyle(
            'MetricVal',
            parent    = styles['Normal'],
            fontSize  = 22,
            leading   = 26,
            textColor = colors.Color(*BRAND_BLUE),
            alignment = TA_CENTER,
        )
        revenue_val = ParagraphStyle(
            'RevenueVal',
            parent    = styles['Normal'],
            fontSize  = 22,
            leading   = 26,
            textColor = colors.Color(0.059, 0.655, 0.502),   # green
            alignment = TA_CENTER,
        )
        summary_data = [[
            Paragraph('TOTAL TRIPS',   metric_label),
            Paragraph('',              metric_label),
            Paragraph('TOTAL REVENUE', metric_label),
        ], [
            Paragraph(str(report.trip_count),         metric_val),
            Paragraph('',                             metric_val),
            Paragraph(f'${report.total_revenue:,.2f}', revenue_val),
        ]]
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 1.5 * inch, 2.5 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.Color(0.98, 0.98, 0.98)),
            ('BOX',           (0, 0), (-1, -1), 0.5, colors.Color(*LIGHT_GREY)),
            ('LINEAFTER',     (0, 0), (0, -1), 0.5, colors.Color(*LIGHT_GREY)),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.25 * inch))

        # ── 4. Trip detail table ──────────────────────────────────────────────
        if report.trips:
            th_style = ParagraphStyle(
                'TH',
                parent    = styles['Normal'],
                fontSize  = 8,
                textColor = colors.Color(*WHITE),
                alignment = TA_LEFT,
            )
            td_style = ParagraphStyle(
                'TD',
                parent    = styles['Normal'],
                fontSize  = 9,
                textColor = colors.Color(*BLACK),
            )
            td_right = ParagraphStyle(
                'TDRight',
                parent    = styles['Normal'],
                fontSize  = 9,
                textColor = colors.Color(0.059, 0.655, 0.502),
                alignment = TA_RIGHT,
            )
            td_muted = ParagraphStyle(
                'TDMuted',
                parent    = styles['Normal'],
                fontSize  = 8,
                textColor = colors.Color(*MID_GREY),
            )

            table_rows = [[
                Paragraph('DATE',    th_style),
                Paragraph('TRIP ID', th_style),
                Paragraph('ROUTE',   th_style),
                Paragraph('STATUS',  th_style),
                Paragraph('REVENUE', ParagraphStyle('THR', parent=th_style, alignment=TA_RIGHT)),
            ]]
            for i, t in enumerate(report.trips):
                table_rows.append([
                    Paragraph(t.trip_date or '—',                td_style),
                    Paragraph(t.trip_id   or '—',                td_muted),
                    Paragraph(t.route     or '—',                td_style),
                    Paragraph(t.status    or '—',                td_muted),
                    Paragraph(f'${t.revenue:,.2f}',              td_right),
                ])

            col_w = [1.1*inch, 1.4*inch, 1.5*inch, 1.4*inch, 1.1*inch]
            detail_table = Table(table_rows, colWidths=col_w, repeatRows=1)
            ts = [
                ('BACKGROUND',    (0, 0), (-1, 0),  colors.Color(*BRAND_BLUE)),
                ('TOPPADDING',    (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
                ('GRID',          (0, 0), (-1, -1), 0.25, colors.Color(*LIGHT_GREY)),
                ('ALIGN',         (4, 0), (4, -1), 'RIGHT'),
            ]
            for row_idx in range(1, len(table_rows)):
                if row_idx % 2 == 0:
                    ts.append(('BACKGROUND', (0, row_idx), (-1, row_idx),
                                colors.Color(*LIGHT_GREY)))
            detail_table.setStyle(TableStyle(ts))
            story.append(detail_table)
            story.append(Spacer(1, 0.15 * inch))
        else:
            no_trips = ParagraphStyle(
                'NoTrips',
                parent    = styles['Normal'],
                fontSize  = 10,
                textColor = colors.Color(*MID_GREY),
                alignment = TA_CENTER,
                spaceAfter= 12,
            )
            story.append(Paragraph('No trips recorded for this reporting window.', no_trips))
            story.append(Spacer(1, 0.15 * inch))

        # ── 5. Grand total footer ─────────────────────────────────────────────
        ft_label = ParagraphStyle(
            'FTLabel',
            parent    = styles['Normal'],
            fontSize  = 10,
            textColor = colors.Color(*WHITE),
        )
        ft_val = ParagraphStyle(
            'FTVal',
            parent    = styles['Normal'],
            fontSize  = 12,
            textColor = colors.Color(*WHITE),
            alignment = TA_RIGHT,
        )
        footer_data = [[
            Paragraph(f'<b>GRAND TOTAL  —  {report.trip_count} trip{"s" if report.trip_count != 1 else ""}</b>',
                      ft_label),
            Paragraph(f'<b>${report.total_revenue:,.2f}</b>', ft_val),
        ]]
        footer_table = Table(footer_data, colWidths=[5.0 * inch, 1.5 * inch])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(*BRAND_BLUE)),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',  (0, 0), (0, 0), 14),
            ('RIGHTPADDING', (-1, 0), (-1, 0), 14),
            ('ALIGN',        (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(footer_table)

        # ── 6. Generated timestamp ────────────────────────────────────────────
        ts_style = ParagraphStyle(
            'Timestamp',
            parent    = styles['Normal'],
            fontSize  = 7,
            textColor = colors.Color(*MID_GREY),
            alignment = TA_RIGHT,
            spaceBefore = 6,
        )
        story.append(Paragraph(
            f'Generated by BCAT Command Center on {datetime.utcnow():%Y-%m-%d %H:%M} UTC',
            ts_style,
        ))

        doc.build(story)
        log.info("PDF generated: %s (%d trips)", out_path, report.trip_count)
        return str(out_path)
