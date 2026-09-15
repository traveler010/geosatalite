"""
SatQuery AI — Report Generator

Creates downloadable reports bundling:
  - Query text
  - Answer
  - Confidence score
  - Evidence details
  - Full execution trace

Supports:
  - PDF output via ReportLab (primary)
  - HTML output (legacy fallback)
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import REPORTS_DIR


# ═══════════════════════════════════════════════════════════
#  PDF Generation (ReportLab)
# ═══════════════════════════════════════════════════════════

def generate_pdf_report(trace: dict, query_id: str) -> str:
    """
    Generate a styled PDF report for a single query.
    Returns the file path of the generated report.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable,
    )

    report_path = REPORTS_DIR / f"report_{query_id}.pdf"

    # ── Colors ──
    bg_dark = HexColor("#080d1a")
    border_color = HexColor("#1e293b")
    text_primary = HexColor("#edf6ff")
    text_muted = HexColor("#91a4bb")
    accent_blue = HexColor("#38bdf8")
    accent_emerald = HexColor("#10b981")
    accent_gold = HexColor("#facc15")
    accent_red = HexColor("#ef4444")

    # ── Confidence ──
    confidence = trace.get("confidence", 0)
    conf_pct = round(confidence * 100, 1)
    conf_color = accent_emerald if confidence >= 0.8 else accent_gold if confidence >= 0.55 else accent_red

    # ── Styles ──
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SatTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=text_primary,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "SatSubtitle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        textColor=text_muted,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SatSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=accent_blue,
        spaceBefore=16,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "SatBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=text_primary,
        leading=14,
        spaceAfter=8,
    )
    query_style = ParagraphStyle(
        "SatQuery",
        parent=body_style,
        textColor=accent_gold,
        fontName="Helvetica-BoldOblique",
        fontSize=11,
    )
    mono_style = ParagraphStyle(
        "SatMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        textColor=text_muted,
        leading=9,
        spaceAfter=4,
    )
    conf_style = ParagraphStyle(
        "SatConf",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=conf_color,
        spaceAfter=8,
    )

    # ── Build Document ──
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f"SatQuery AI Report — {query_id}",
        author="SatQuery AI",
    )

    elements = []

    # Header
    elements.append(Paragraph("🛰️ SatQuery AI — Analysis Report", title_style))
    elements.append(Paragraph(
        f"Query ID: {query_id}  ·  {trace.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}  ·  "
        f"Status: {trace.get('status', 'N/A').upper()}",
        subtitle_style,
    ))
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=border_color, spaceAfter=12,
    ))

    # Query
    elements.append(Paragraph("QUERY", section_style))
    elements.append(Paragraph(
        _escape(trace.get("query", "N/A")),
        query_style,
    ))

    # Answer
    elements.append(Paragraph("ANSWER", section_style))
    answer_text = trace.get("answer", "N/A")
    # Wrap long answers
    for para in answer_text.split("\n"):
        if para.strip():
            elements.append(Paragraph(_escape(para.strip()), body_style))

    # Confidence
    elements.append(Paragraph("CONFIDENCE", section_style))
    elements.append(Paragraph(f"{conf_pct}%", conf_style))

    # Pipeline Details
    elements.append(Paragraph("PIPELINE EXECUTION", section_style))
    pipeline_data = [
        ["Task Type", str(trace.get("selected_task", "N/A"))],
        ["Tool Used", str(trace.get("selected_tool", "N/A"))],
        ["Processing Time", f"{trace.get('processing_time_ms', 'N/A')} ms"],
        ["Parameters", str(trace.get("parameters_used", {}))],
    ]
    pipeline_table = Table(pipeline_data, colWidths=[120, 350])
    pipeline_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), text_muted),
        ("TEXTCOLOR", (1, 0), (1, -1), text_primary),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, border_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(pipeline_table)

    # Evidence
    evidence = trace.get("evidence", {})
    if evidence:
        elements.append(Paragraph("EVIDENCE", section_style))
        evidence_data = []
        for key, value in evidence.items():
            if isinstance(value, dict):
                val_str = ", ".join(f"{k}: {v}" for k, v in value.items())
            elif isinstance(value, list):
                val_str = f"{len(value)} items"
            else:
                val_str = str(value)
            evidence_data.append([str(key), val_str])

        if evidence_data:
            ev_table = Table(evidence_data, colWidths=[120, 350])
            ev_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), text_muted),
                ("TEXTCOLOR", (1, 0), (1, -1), text_primary),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(ev_table)

    # Full Trace JSON
    elements.append(Paragraph("EXECUTION TRACE (JSON)", section_style))
    trace_json = json.dumps(trace, indent=2, default=str)
    # Wrap long lines for PDF
    wrapped_lines = []
    for line in trace_json.split("\n"):
        if len(line) > 100:
            wrapped_lines.extend(textwrap.wrap(line, width=100))
        else:
            wrapped_lines.append(line)
    trace_text = "\n".join(wrapped_lines)
    elements.append(Paragraph(
        _escape(trace_text).replace("\n", "<br/>"),
        mono_style,
    ))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(
        width="100%", thickness=0.3, color=border_color, spaceAfter=8,
    ))
    footer_style = ParagraphStyle(
        "SatFooter",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        textColor=text_muted,
        alignment=1,  # center
    )
    elements.append(Paragraph(
        f"SatQuery AI · ISRO Multimodal Remote Sensing Assistant · "
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style,
    ))

    doc.build(elements)
    return str(report_path)


def _escape(text: str) -> str:
    """Escape XML/HTML special characters for ReportLab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ═══════════════════════════════════════════════════════════
#  HTML Generation (Legacy Fallback)
# ═══════════════════════════════════════════════════════════

def generate_html_report(trace: dict, query_id: str) -> str:
    """
    Generate an HTML report for a single query (legacy fallback).
    Returns the file path of the generated report.
    """
    report_path = REPORTS_DIR / f"report_{query_id}.html"

    confidence = trace.get("confidence", 0)
    conf_pct = round(confidence * 100, 1)
    conf_color = "#10b981" if confidence >= 0.8 else "#facc15" if confidence >= 0.55 else "#ef4444"

    evidence = trace.get("evidence", {})
    evidence_html = ""
    for key, value in evidence.items():
        if isinstance(value, dict):
            val_str = "<br>".join(f"&nbsp;&nbsp;{k}: {v}" for k, v in value.items())
        elif isinstance(value, list):
            val_str = f"{len(value)} items"
        else:
            val_str = str(value)
        evidence_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">{key}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{val_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SatQuery AI — Analysis Report {query_id}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #080d1a;
            color: #edf6ff;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 24px; background: rgba(9, 17, 31, 0.88);
            border: 1px solid #1e293b; border-radius: 12px; margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 20px; font-weight: 700; }}
        .badge {{
            padding: 6px 14px; border-radius: 20px;
            font-size: 11px; font-weight: 600; font-family: monospace;
            background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); color: #a7f3d0;
        }}
        .card {{
            background: rgba(9, 17, 31, 0.88); border: 1px solid #1e293b;
            border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
        }}
        .card h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: #91a4bb; margin-bottom: 12px; }}
        .answer {{ font-size: 15px; line-height: 1.7; color: #edf6ff; }}
        .confidence-bar {{ height: 6px; background: #1e293b; border-radius: 3px; margin-top: 8px; overflow: hidden; }}
        .confidence-fill {{ height: 100%; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        .trace-json {{
            background: #06101b; border: 1px solid #1e293b; border-radius: 8px;
            padding: 16px; font-family: monospace; font-size: 11px; color: #91a4bb;
            overflow-x: auto; white-space: pre-wrap; word-break: break-word;
        }}
        .footer {{ text-align: center; padding: 20px; color: #60738c; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🛰️ SatQuery AI Report</h1>
                <p style="color:#91a4bb;font-size:12px;margin-top:4px;">
                    Query ID: {query_id} · {trace.get('timestamp', 'N/A')}
                </p>
            </div>
            <div class="badge">{trace.get('status', 'N/A').upper()}</div>
        </div>
        <div class="card"><h2>Query</h2><p class="answer" style="color:#f5e9b9;">{trace.get('query', 'N/A')}</p></div>
        <div class="card"><h2>Answer</h2><p class="answer">{trace.get('answer', 'N/A')}</p></div>
        <div class="card">
            <h2>Confidence</h2>
            <p style="font-size:24px;font-weight:700;color:{conf_color};">{conf_pct}%</p>
            <div class="confidence-bar"><div class="confidence-fill" style="width:{conf_pct}%;background:{conf_color};"></div></div>
        </div>
        <div class="card">
            <h2>Pipeline Execution</h2>
            <table>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Task Type</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#38bdf8;font-size:12px;font-weight:600;">{trace.get('selected_task', 'N/A')}</td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Tool Used</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{trace.get('selected_tool', 'N/A')}</td></tr>
                <tr><td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Processing Time</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{trace.get('processing_time_ms', 'N/A')} ms</td></tr>
            </table>
        </div>
        {'<div class="card"><h2>Evidence</h2><table>' + evidence_html + '</table></div>' if evidence_html else ''}
        <div class="card">
            <h2>Execution Trace (JSON)</h2>
            <div class="trace-json">{_format_trace_json(trace)}</div>
        </div>
        <div class="footer">
            SatQuery AI · ISRO Multimodal Remote Sensing Assistant · Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""

    report_path.write_text(html, encoding="utf-8")
    return str(report_path)


def _format_trace_json(trace: dict) -> str:
    """Pretty-format a trace dict for display, escaping HTML."""
    formatted = json.dumps(trace, indent=2, default=str)
    return formatted.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ═══════════════════════════════════════════════════════════
#  Report Path Lookup
# ═══════════════════════════════════════════════════════════

def get_report_path(query_id: str, fmt: str = "pdf") -> Optional[str]:
    """Check if a report exists for the given query_id."""
    ext = ".pdf" if fmt == "pdf" else ".html"
    path = REPORTS_DIR / f"report_{query_id}{ext}"
    if path.exists():
        return str(path)
    # Fallback: check for the other format
    alt_ext = ".html" if fmt == "pdf" else ".pdf"
    alt_path = REPORTS_DIR / f"report_{query_id}{alt_ext}"
    if alt_path.exists():
        return str(alt_path)
    return None
