"""
SatQuery AI — Report Generator

Creates downloadable PDF reports using ReportLab, bundling:
  - Query text
  - Answer
  - Confidence score
  - Evidence details
  - Full execution trace
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import REPORTS_DIR


def generate_html_report(trace: dict, query_id: str) -> str:
    """
    Generate an HTML report for a single query.
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
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px;
            background: rgba(9, 17, 31, 0.88);
            border: 1px solid #1e293b;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 700;
        }}
        .header .badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            font-family: monospace;
        }}
        .card {{
            background: rgba(9, 17, 31, 0.88);
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;
        }}
        .card h2 {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #91a4bb;
            margin-bottom: 12px;
        }}
        .answer {{
            font-size: 15px;
            line-height: 1.7;
            color: #edf6ff;
        }}
        .confidence-bar {{
            height: 6px;
            background: #1e293b;
            border-radius: 3px;
            margin-top: 8px;
            overflow: hidden;
        }}
        .confidence-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .trace-json {{
            background: #06101b;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 16px;
            font-family: monospace;
            font-size: 11px;
            color: #91a4bb;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #60738c;
            font-size: 11px;
        }}
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
            <div class="badge" style="background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);color:#a7f3d0;">
                {trace.get('status', 'N/A').upper()}
            </div>
        </div>

        <!-- Query -->
        <div class="card">
            <h2>Query</h2>
            <p class="answer" style="color:#f5e9b9;">{trace.get('query', 'N/A')}</p>
        </div>

        <!-- Answer -->
        <div class="card">
            <h2>Answer</h2>
            <p class="answer">{trace.get('answer', 'N/A')}</p>
        </div>

        <!-- Confidence -->
        <div class="card">
            <h2>Confidence</h2>
            <p style="font-size:24px;font-weight:700;color:{conf_color};">{conf_pct}%</p>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width:{conf_pct}%;background:{conf_color};"></div>
            </div>
        </div>

        <!-- Pipeline Details -->
        <div class="card">
            <h2>Pipeline Execution</h2>
            <table>
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Task Type</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#38bdf8;font-size:12px;font-weight:600;">{trace.get('selected_task', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Tool Used</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{trace.get('selected_tool', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Processing Time</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{trace.get('processing_time_ms', 'N/A')} ms</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#91a4bb;font-size:12px;">Parameters</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #1e293b;color:#edf6ff;font-size:12px;">{trace.get('parameters_used', {})}</td>
                </tr>
            </table>
        </div>

        <!-- Evidence -->
        {f'''<div class="card">
            <h2>Evidence</h2>
            <table>{evidence_html}</table>
        </div>''' if evidence_html else ''}

        <!-- Full Trace -->
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
    import json
    formatted = json.dumps(trace, indent=2, default=str)
    return formatted.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_report_path(query_id: str) -> Optional[str]:
    """Check if a report exists for the given query_id."""
    path = REPORTS_DIR / f"report_{query_id}.html"
    if path.exists():
        return str(path)
    return None
