"""
PDF Generator — TMF Intelligence System
========================================
Generates professionally formatted PDFs for:
- Executive Summaries
- Draft Communications (emails)
- TMF Status Reports

Uses reportlab with TrialAxis CRO brand colors.
"""

import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── TrialAxis CRO Brand Colors ────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1B3A5C")
ORANGE = colors.HexColor("#E8622A")
LIGHT  = colors.HexColor("#F7F9FB")
GREY   = colors.HexColor("#6B7280")
WHITE  = colors.white
RED    = colors.HexColor("#DC2626")
AMBER  = colors.HexColor("#D97706")
GREEN  = colors.HexColor("#059669")

# ── Styles ────────────────────────────────────────────────────────────────────
def get_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Normal"],
            fontSize=22, fontName="Helvetica-Bold",
            textColor=NAVY, leading=26, spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=10, fontName="Helvetica",
            textColor=GREY, leading=14, spaceAfter=16
        ),
        "section": ParagraphStyle(
            "section", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=ORANGE, leading=12,
            spaceBefore=14, spaceAfter=6,
            textTransform="uppercase", letterSpacing=1.5
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=colors.HexColor("#1F2937"),
            leading=14, spaceAfter=6
        ),
        "bold": ParagraphStyle(
            "bold", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=NAVY, leading=14, spaceAfter=4
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=GREY, leading=11, spaceAfter=4
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, fontName="Helvetica",
            textColor=GREY, alignment=TA_CENTER
        ),
    }
    return styles


def header_footer(canvas, doc):
    """Page header and footer on every page"""
    canvas.saveState()
    width, height = A4

    # Header — navy bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 1.8*cm, width, 1.8*cm, fill=1, stroke=0)

    # Header text
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(1.5*cm, height - 1.1*cm, "TrialAxis CRO")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93C5FD"))
    canvas.drawString(1.5*cm, height - 1.5*cm, "TMF Intelligence System  ·  Internal Use Only")

    # Orange accent line
    canvas.setFillColor(ORANGE)
    canvas.rect(0, height - 1.85*cm, width, 0.15*cm, fill=1, stroke=0)

    # Footer
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 7)
    today = datetime.now().strftime("%B %d, %Y")
    canvas.drawString(1.5*cm, 0.8*cm, f"Generated: {today}  ·  TrialAxis CRO  ·  ICH E6 GCP Compliant")
    canvas.drawRightString(width - 1.5*cm, 0.8*cm, f"Page {doc.page}")

    # Footer line
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(1.5*cm, 1.1*cm, width - 1.5*cm, 1.1*cm)

    canvas.restoreState()


def markdown_to_paragraphs(text, styles):
    """Convert basic markdown to reportlab paragraphs"""
    story = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Headers
        if line.startswith('### '):
            story.append(Paragraph(line[4:], styles["section"]))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], styles["section"]))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], styles["bold"]))

        # Bullet points
        elif line.startswith('- ') or line.startswith('* '):
            text_content = line[2:]
            text_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_content)
            story.append(Paragraph(f"&nbsp;&nbsp;&#8226;&nbsp; {text_content}", styles["body"]))

        # Numbered list
        elif re.match(r'^\d+\.', line):
            text_content = re.sub(r'^\d+\.\s*', '', line)
            text_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text_content)
            num = re.match(r'^(\d+)\.', line).group(1)
            story.append(Paragraph(f"&nbsp;&nbsp;<b>{num}.</b>&nbsp; {text_content}", styles["body"]))

        # Table rows — basic markdown table support
        elif line.startswith('|'):
            # Collect all table rows
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = lines[i].strip()
                if '---' in row:
                    i += 1
                    continue
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    table_rows.append(cells)
                i += 1

            if table_rows:
                # Style header row
                header = [Paragraph(f'<b>{c}</b>', styles["small"]) for c in table_rows[0]]
                data = [header]
                for row in table_rows[1:]:
                    data.append([Paragraph(c, styles["small"]) for c in row])

                col_count = max(len(r) for r in data)
                col_width = (A4[0] - 3*cm) / col_count

                tbl = Table(data, colWidths=[col_width] * col_count)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), NAVY),
                    ('TEXTCOLOR', (0,0), (-1,0), WHITE),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT]),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 8))
            continue

        # Normal paragraph with bold support
        else:
            text_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            story.append(Paragraph(text_content, styles["body"]))

        i += 1

    return story


def generate_executive_summary_pdf(summary_text, title, audience, today):
    """Generate a formatted PDF for executive summary"""
    buffer = io.BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
        title=f"Executive Summary — {title}",
        author="TrialAxis CRO TMF Intelligence System"
    )

    story = []

    # Title block
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("EXECUTIVE SUMMARY", styles["section"]))
    story.append(Paragraph(title, styles["title"]))
    story.append(Paragraph(f"{today}  ·  {audience}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=12))

    # Summary content
    content_paragraphs = markdown_to_paragraphs(summary_text, styles)
    story.extend(content_paragraphs)

    # Confidentiality footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=6))
    story.append(Paragraph(
        "CONFIDENTIAL — TrialAxis CRO Internal Use Only · Not for external distribution",
        styles["footer"]
    ))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_email_pdf(draft_text, study_name, document_name, today):
    """Generate a formatted PDF for a drafted communication"""
    buffer = io.BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm,
        title=f"TMF Communication — {study_name}",
        author="TrialAxis CRO TMF Intelligence System"
    )

    story = []
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("DRAFTED COMMUNICATION", styles["section"]))
    story.append(Paragraph(f"Study: {study_name}", styles["title"]))
    story.append(Paragraph(f"Re: {document_name}  ·  {today}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=12))

    # Email content in a light box
    email_data = [[Paragraph(line if line.strip() else "&nbsp;", styles["body"])]
                  for line in draft_text.split('\n')]

    email_table = Table(email_data, colWidths=[A4[0] - 3*cm])
    email_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E5E7EB")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(email_table)

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=6))
    story.append(Paragraph("CONFIDENTIAL — TrialAxis CRO Internal Use Only", styles["footer"]))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return buffer.getvalue()