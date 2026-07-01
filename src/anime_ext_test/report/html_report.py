"""HTML report writer — generate a self-contained, styled HTML report from RunReport."""

from __future__ import annotations

import html as html_lib
from pathlib import Path

from anime_ext_test.models import RunReport, RunSummary

_STATUS_ICONS = {"pass": "&#x2705;", "fail": "&#x274C;", "skip": "&#x23ED;", "error": "&#x26A0;"}
_STATUS_LABELS = {"pass": "Passed", "fail": "Failed", "skip": "Skipped", "error": "Error"}
_STATUS_COLORS = {"pass": "#22c55e", "fail": "#ef4444", "skip": "#6b7280", "error": "#f59e0b"}


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def _compute_theme_breakdown(report: RunReport) -> dict[str, dict]:
    themes: dict[str, dict] = {}
    for er in report.extensions:
        theme_key = er.extension.theme_pkg or "legacy"
        t = themes.setdefault(theme_key, {"ext_count": 0, "passed": 0, "failed": 0, "total": 0})
        t["ext_count"] += 1
        t["passed"] += er.passed
        t["failed"] += er.failed
        t["total"] += er.total
    return themes


def _build_donut_svg(passed: int, failed: int, skipped: int, errors: int) -> str:
    total = passed + failed + skipped + errors
    if total == 0:
        return """<svg viewBox="0 0 120 120" class="donut-svg">
  <circle cx="60" cy="60" r="45" fill="none" stroke="var(--surface2)" stroke-width="12"/>
  <text x="60" y="56" text-anchor="middle" fill="var(--text)" font-size="18" font-weight="700">0%</text>
  <text x="60" y="72" text-anchor="middle" fill="var(--text-muted)" font-size="9">health</text>
</svg>"""
    # stroke-dasharray = circumference, stroke-dashoffset = circumference * (1 - fraction)
    # circumference = 2 * pi * 45 ≈ 282.74
    circ = 2 * 3.14159265 * 45
    health_pct = passed / total * 100

    segments = [
        ("pass", passed, "var(--pass)"),
        ("fail", failed, "var(--fail)"),
        ("skip", skipped, "var(--skip)"),
        ("error", errors, "var(--error)"),
    ]
    offset = 0
    circles = ""
    for key, count, color in segments:
        if count == 0:
            continue
        frac = count / total
        dash = circ * frac
        # rotate -90 to start from top; offset via stroke-dashoffset
        rotation = -90 + (offset / total * 360)
        circles += f"""<circle cx="60" cy="60" r="45" fill="none" stroke="{color}" stroke-width="12"
            stroke-dasharray="{dash} {circ - dash}" stroke-dashoffset="{-offset / total * circ}"
            transform="rotate({rotation} 60 60)"/>"""
        offset += count

    return f"""<svg viewBox="0 0 120 120" class="donut-svg">
  <circle cx="60" cy="60" r="45" fill="none" stroke="var(--surface2)" stroke-width="12"/>
  {circles}
  <text x="60" y="56" text-anchor="middle" fill="var(--text)" font-size="18" font-weight="700">{health_pct:.0f}%</text>
  <text x="60" y="72" text-anchor="middle" fill="var(--text-muted)" font-size="9">health</text>
</svg>"""


def write_html_report(report: RunReport, summary: RunSummary, output_dir: Path) -> Path:
    """Write a self-contained HTML report with CSS and JS inline. Returns the output path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"report-{report.run_id}.html"

    page = _build_html(report, summary)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    return out_path


def _build_html(report: RunReport, summary: RunSummary) -> str:
    started = report.started_at.isoformat() if report.started_at else "N/A"
    finished = report.finished_at.isoformat() if report.finished_at else "N/A"
    duration_str = _format_duration(summary.duration_seconds)

    cat_rows = ""
    for cat in sorted(summary.by_test_type):
        s = summary.by_test_type[cat]
        cat_rows += f"""
            <tr>
                <td class="cat-name">{html_lib.escape(cat)}</td>
                <td class="num pass">{s['passed']}</td>
                <td class="num fail">{s['failed']}</td>
                <td class="num skip">{s['skipped']}</td>
                <td class="num error">{s['errors']}</td>
            </tr>"""

    lang_rows = ""
    for lang in sorted(summary.by_language):
        s = summary.by_language[lang]
        lang_rows += f"""
            <tr>
                <td class="lang-code">{html_lib.escape(lang)}</td>
                <td class="num pass">{s['passed']}</td>
                <td class="num fail">{s['failed']}</td>
                <td class="num skip">{s['skipped']}</td>
                <td class="num error">{s['errors']}</td>
                <td class="num">{s['total']}</td>
            </tr>"""

    theme_data = _compute_theme_breakdown(report)
    theme_rows = ""
    for theme_name in sorted(theme_data):
        t = theme_data[theme_name]
        pass_pct = (t["passed"] / t["total"] * 100) if t["total"] else 0
        fail_pct = (t["failed"] / t["total"] * 100) if t["total"] else 0
        avg_health = pass_pct
        theme_rows += f"""
            <tr>
                <td class="theme-name">{html_lib.escape(theme_name)}</td>
                <td class="num">{t['ext_count']}</td>
                <td class="num pass">{pass_pct:.0f}%</td>
                <td class="num fail">{fail_pct:.0f}%</td>
                <td class="num">{avg_health:.0f}%</td>
            </tr>"""

    cat_cards = ""
    for cat in sorted(summary.by_test_type):
        s = summary.by_test_type[cat]
        total_cat = s["passed"] + s["failed"] + s["skipped"] + s["errors"]
        pass_width = (s["passed"] / total_cat * 100) if total_cat else 0
        fail_width = (s["failed"] / total_cat * 100) if total_cat else 0
        cat_cards += f"""
        <div class="cat-stat-card">
            <div class="cat-stat-name">{html_lib.escape(cat)}</div>
            <div class="cat-stat-counts">
                <span class="pass">{s['passed']}p</span>
                <span class="fail">{s['failed']}f</span>
            </div>
            <div class="mini-bar">
                <div class="mini-bar-pass" style="width:{pass_width:.1f}%"></div>
                <div class="mini-bar-fail" style="width:{fail_width:.1f}%"></div>
            </div>
        </div>"""

    failure_items = ""
    for er in sorted(report.extensions, key=lambda e: e.extension.module_id):
        if er.failed == 0 and er.errored == 0:
            continue
        ext = er.extension
        health_pct = (er.passed / er.total * 100) if er.total else 0
        if health_pct >= 80:
            health_color = _STATUS_COLORS["pass"]
        elif health_pct < 50:
            health_color = _STATUS_COLORS["error"]
        else:
            health_color = _STATUS_COLORS["skip"]
        fail_details = ""
        for r in er.results:
            if r.status in ("fail", "error"):
                msg = html_lib.escape(r.message) if r.message else ""
                fail_details += f"""<div class="fail-item">
                    <span class="fail-item-name">{html_lib.escape(r.test_name)}</span>
                    <span class="fail-item-msg">{msg}</span>
                </div>"""
        failure_items += f"""
        <div class="failure-ext">
            <div class="failure-ext-header">
                <span class="health-dot" style="background:{health_color}"></span>
                <code>{html_lib.escape(ext.module_id)}</code>
                <span class="health-pct" style="color:{health_color}">{health_pct:.0f}%</span>
            </div>
            <div class="failure-ext-details">{fail_details}</div>
        </div>"""

    ext_cards = ""
    for er in sorted(report.extensions, key=lambda e: e.extension.module_id):
        ext = er.extension
        total = er.total
        passed = er.passed
        failed = er.failed
        skipped = er.skipped
        errored = er.errored
        health_pct = (passed / total * 100) if total else 0
        if health_pct >= 80:
            health_color = _STATUS_COLORS["pass"]
        elif health_pct < 50:
            health_color = _STATUS_COLORS["error"]
        else:
            health_color = _STATUS_COLORS["skip"]

        result_rows = ""
        for r in er.results:
            icon = _STATUS_ICONS.get(r.status, "?")
            color = _STATUS_COLORS.get(r.status, "#666")
            msg = html_lib.escape(r.message) if r.message else ""
            detail = html_lib.escape(r.detail) if r.detail and r.status in ("fail", "error") else ""
            result_rows += f"""
                <tr class="result-row result-{r.status}" data-status="{r.status}">
                    <td class="result-icon" style="color:{color}">{icon}</td>
                    <td class="result-name">{html_lib.escape(r.test_name)}</td>
                    <td class="result-duration">{r.duration_ms:.0f}ms</td>
                    <td class="result-msg">{msg}</td>
                    <td class="result-detail">{detail}</td>
                </tr>"""

        theme_label = html_lib.escape(ext.theme_pkg or "legacy")
        base_url = html_lib.escape(ext.base_url or "N/A")

        ext_cards += f"""
        <div class="ext-card" id="ext-{html_lib.escape(ext.module_id)}">
            <div class="ext-header" onclick="toggleCard(this)" role="button" tabindex="0" aria-label="Toggle {html_lib.escape(ext.module_id)}" aria-expanded="false">
                <div class="ext-title">
                    <span class="health-dot" style="background:{health_color}"></span>
                    <code class="ext-id">{html_lib.escape(ext.module_id)}</code>
                    <span class="ext-name">{html_lib.escape(ext.ext_name)}</span>
                </div>
                <div class="ext-stats">
                    <span class="stat pass">{passed}p</span>
                    <span class="stat fail">{failed}f</span>
                    <span class="stat skip">{skipped}s</span>
                    <span class="stat error">{errored}e</span>
                    <span class="health-pct" style="color:{health_color}">{health_pct:.0f}%</span>
                </div>
            </div>
            <div class="ext-body collapsed" aria-expanded="false">
                <div class="ext-meta">
                    <span>Lang: <code>{html_lib.escape(ext.lang)}</code></span>
                    <span>Theme: <code>{theme_label}</code></span>
                    <span>Base URL: <code>{base_url}</code></span>
                    <span>NSFW: {ext.is_nsfw}</span>
                </div>
                <table class="results-table">
                    <thead>
                        <tr><th></th><th>Test</th><th>Time</th><th>Message</th><th>Detail</th></tr>
                    </thead>
                    <tbody>{result_rows}</tbody>
                </table>
            </div>
        </div>"""

    donut_svg = _build_donut_svg(summary.passed, summary.failed, summary.skipped, summary.errors)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Anime Extensions Test Report &mdash; {html_lib.escape(report.run_id)}</title>
<style>
:root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --surface2: #334155;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --border: #475569;
    --pass: #22c55e;
    --fail: #ef4444;
    --skip: #6b7280;
    --error: #f59e0b;
    --accent: #38bdf8;
}}
.light-theme {{
    --bg: #ffffff;
    --surface: #f8fafc;
    --surface2: #e2e8f0;
    --text: #0f172a;
    --text-muted: #475569;
    --border: #cbd5e1;
    --pass: #16a34a;
    --fail: #dc2626;
    --skip: #6b7280;
    --error: #d97706;
    --accent: #0284c7;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}}
.skip-nav {{
    position: absolute;
    top: -100px;
    left: 0;
    background: var(--accent);
    color: #fff;
    padding: 0.5rem 1rem;
    z-index: 1000;
    text-decoration: none;
    font-size: 0.85rem;
    border-radius: 0 0 0.25rem 0;
}}
.skip-nav:focus {{ top: 0; }}

/* Layout with sticky nav */
.layout {{
    display: flex;
    min-height: 100vh;
}}
.toc-nav {{
    position: sticky;
    top: 0;
    width: 200px;
    min-width: 200px;
    height: 100vh;
    overflow-y: auto;
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 1rem 0;
    flex-shrink: 0;
}}
.toc-nav h2 {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    padding: 0 1rem 0.5rem;
}}
.toc-nav a {{
    display: block;
    padding: 0.4rem 1rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.8rem;
    border-left: 3px solid transparent;
    transition: all 0.15s;
}}
.toc-nav a:hover, .toc-nav a.active {{
    color: var(--accent);
    border-left-color: var(--accent);
    background: rgba(56, 189, 248, 0.05);
}}
.main-content {{
    flex: 1;
    padding: 1rem 1.5rem;
    max-width: 1000px;
}}

/* Mobile nav */
@media (max-width: 800px) {{
    .layout {{ flex-direction: column; }}
    .toc-nav {{
        position: sticky;
        top: 0;
        width: 100%;
        min-width: unset;
        height: auto;
        overflow-x: auto;
        overflow-y: hidden;
        white-space: nowrap;
        border-right: none;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 0;
        padding: 0.5rem 0;
    }}
    .toc-nav h2 {{ display: none; }}
    .toc-nav a {{
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-left: none;
        border-bottom: 2px solid transparent;
        font-size: 0.75rem;
    }}
    .toc-nav a:hover, .toc-nav a.active {{
        border-left-color: transparent;
        border-bottom-color: var(--accent);
    }}
    .main-content {{ padding: 1rem; }}
}}

/* Header */
.header {{
    text-align: center;
    padding: 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
    position: relative;
}}
.header h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; }}
.header .meta {{ color: var(--text-muted); font-size: 0.85rem; }}
.header .meta code {{ color: var(--accent); }}
.theme-toggle {{
    position: absolute;
    top: 1rem;
    right: 0;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.35rem 0.75rem;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
}}
.theme-toggle:hover {{ border-color: var(--accent); }}

/* Hero section with donut */
.hero {{
    display: flex;
    align-items: center;
    gap: 2rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}}
.donut-wrap {{
    flex-shrink: 0;
    width: 140px;
    height: 140px;
}}
.donut-svg {{ width: 100%; height: 100%; }}
.donut-legend {{
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.8rem;
}}
.donut-legend-item {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.donut-legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
}}

/* Summary cards */
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}}
.summary-card {{
    background: var(--surface);
    border-radius: 0.5rem;
    padding: 1.25rem;
    text-align: center;
    border: 1px solid var(--border);
}}
.summary-card .value {{ font-size: 2rem; font-weight: 700; }}
.summary-card .label {{
    font-size: 0.75rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem;
}}
.summary-card.pass .value {{ color: var(--pass); }}
.summary-card.fail .value {{ color: var(--fail); }}
.summary-card.skip .value {{ color: var(--skip); }}
.summary-card.error .value {{ color: var(--error); }}

/* Per-category stat cards */
.cat-stats-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 2rem;
}}
.cat-stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.375rem;
    padding: 0.6rem 0.85rem;
    min-width: 120px;
    flex: 1;
}}
.cat-stat-name {{
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.25rem;
}}
.cat-stat-counts {{
    font-size: 0.7rem;
    margin-bottom: 0.35rem;
}}
.cat-stat-counts .pass {{ color: var(--pass); }}
.cat-stat-counts .fail {{ color: var(--fail); }}
.mini-bar {{
    height: 4px;
    background: var(--surface2);
    border-radius: 2px;
    display: flex;
    overflow: hidden;
}}
.mini-bar-pass {{ background: var(--pass); }}
.mini-bar-fail {{ background: var(--fail); }}

/* Breakdown tables */
.breakdowns {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
}}
@media (max-width: 800px) {{ .breakdowns {{ grid-template-columns: 1fr; }} }}
.breakdown {{
    background: var(--surface);
    border-radius: 0.5rem;
    border: 1px solid var(--border);
    overflow: hidden;
}}
.breakdown h3 {{
    padding: 0.75rem 1rem;
    background: var(--surface2);
    font-size: 0.85rem;
    border-bottom: 1px solid var(--border);
}}
.breakdown table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.breakdown th {{
    text-align: left; padding: 0.5rem 0.75rem;
    color: var(--text-muted); font-weight: 600;
    border-bottom: 1px solid var(--border);
}}
.breakdown td {{ padding: 0.4rem 0.75rem; }}
.breakdown td.num {{ text-align: center; font-variant-numeric: tabular-nums; }}
.breakdown td.num.pass {{ color: var(--pass); }}
.breakdown td.num.fail {{ color: var(--fail); }}
.breakdown td.num.skip {{ color: var(--skip); }}
.breakdown td.num.error {{ color: var(--error); }}

/* Theme breakdown */
.theme-breakdown {{
    background: var(--surface);
    border-radius: 0.5rem;
    border: 1px solid var(--border);
    overflow: hidden;
    margin-bottom: 2rem;
}}
.theme-breakdown h3 {{
    padding: 0.75rem 1rem;
    background: var(--surface2);
    font-size: 0.85rem;
    border-bottom: 1px solid var(--border);
}}
.theme-breakdown table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.theme-breakdown th {{
    text-align: left; padding: 0.5rem 0.75rem;
    color: var(--text-muted); font-weight: 600;
    border-bottom: 1px solid var(--border);
}}
.theme-breakdown td {{ padding: 0.4rem 0.75rem; }}
.theme-breakdown td.num {{ text-align: center; font-variant-numeric: tabular-nums; }}
.theme-breakdown td.num.pass {{ color: var(--pass); }}
.theme-breakdown td.num.fail {{ color: var(--fail); }}

/* Failure summary panel */
.failure-panel {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    margin-bottom: 2rem;
    overflow: hidden;
}}
.failure-panel-header {{
    padding: 0.75rem 1rem;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85rem;
    font-weight: 600;
}}
.failure-panel-header:hover {{ background: rgba(239, 68, 68, 0.1); }}
.failure-panel-body {{
    display: none;
    padding: 0.75rem 1rem;
}}
.failure-panel-body.expanded {{ display: block; }}
.failure-ext {{
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(71, 85, 105, 0.3);
}}
.failure-ext:last-child {{ border-bottom: none; }}
.failure-ext-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
}}
.failure-ext-header code {{ color: var(--accent); }}
.failure-ext-header .health-pct {{ font-weight: 600; font-size: 0.75rem; }}
.failure-ext-details {{ padding: 0.25rem 0 0.25rem 1.25rem; }}
.fail-item {{
    font-size: 0.75rem;
    display: flex;
    gap: 0.5rem;
    padding: 0.15rem 0;
}}
.fail-item-name {{
    color: var(--fail);
    font-family: 'SF Mono', 'Fira Code', monospace;
    white-space: nowrap;
}}
.fail-item-msg {{
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

/* Filters toolbar */
.filters {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 1rem;
    padding: 0.75rem 1rem;
    background: var(--surface);
    border-radius: 0.5rem;
    border: 1px solid var(--border);
}}
.filters label {{ font-size: 0.8rem; color: var(--text-muted); }}
.filters input[type="text"] {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 0.25rem;
    color: var(--text);
    padding: 0.35rem 0.5rem;
    font-size: 0.8rem;
    width: 180px;
}}
.filter-btn {{
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 0.35rem 0.75rem;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
}}
.filter-btn:hover, .filter-btn.active {{
    color: var(--text);
    border-color: var(--accent);
    background: rgba(56, 189, 248, 0.1);
}}

/* Extension cards */
.ext-card {{
    background: var(--surface);
    border-radius: 0.5rem;
    border: 1px solid var(--border);
    margin-bottom: 0.5rem;
    overflow: hidden;
}}
.ext-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    cursor: pointer;
    user-select: none;
}}
.ext-header:hover {{ background: var(--surface2); }}
.ext-header:focus {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
.ext-title {{ display: flex; align-items: center; gap: 0.5rem; }}
.ext-title .health-dot {{
    width: 10px; height: 10px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
}}
.ext-title .ext-id {{ font-size: 0.85rem; color: var(--accent); }}
.ext-title .ext-name {{ font-size: 0.85rem; color: var(--text-muted); }}
.ext-stats {{ display: flex; gap: 0.5rem; font-size: 0.75rem; font-variant-numeric: tabular-nums; }}
.ext-stats .stat.pass {{ color: var(--pass); }}
.ext-stats .stat.fail {{ color: var(--fail); }}
.ext-stats .stat.skip {{ color: var(--skip); }}
.ext-stats .stat.error {{ color: var(--error); }}
.ext-stats .health-pct {{ font-weight: 600; }}

.ext-body {{ padding: 0 1rem 1rem; border-top: 1px solid var(--border); }}
.ext-body.collapsed {{ display: none; }}
.ext-meta {{
    display: flex; gap: 1.5rem; flex-wrap: wrap;
    padding: 0.75rem 0; font-size: 0.8rem; color: var(--text-muted);
}}
.ext-meta code {{ color: var(--accent); background: var(--surface2); padding: 0.1rem 0.3rem; border-radius: 0.2rem; }}

.results-table {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; }}
.results-table th {{
    text-align: left; padding: 0.4rem 0.5rem;
    color: var(--text-muted); font-weight: 600; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border);
}}
.results-table td {{ padding: 0.3rem 0.5rem; border-bottom: 1px solid rgba(71, 85, 105, 0.3); }}
.results-table .result-icon {{ width: 24px; text-align: center; }}
.results-table .result-duration {{
    width: 60px; text-align: right;
    color: var(--text-muted); font-variant-numeric: tabular-nums;
}}
.results-table .result-name {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.75rem; }}
.results-table .result-msg {{
    color: var(--text-muted); max-width: 300px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.results-table .result-detail {{
    font-family: monospace; font-size: 0.7rem; color: var(--fail);
    max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}

.result-fail {{ background: rgba(239, 68, 68, 0.05); }}
.result-error {{ background: rgba(245, 158, 11, 0.05); }}
.result-pass {{ display: none; }}
.result-pass.show-pass {{ display: table-row; }}

/* Footer */
.footer {{
    text-align: center;
    padding: 2rem 0;
    color: var(--text-muted);
    font-size: 0.75rem;
    border-top: 1px solid var(--border);
    margin-top: 2rem;
}}

/* Print styles */
@media print {{
    .toc-nav, .theme-toggle, .filters, .skip-nav {{ display: none !important; }}
    .layout {{ display: block !important; }}
    .main-content {{ max-width: 100% !important; padding: 0 !important; }}
    html {{ --bg: #ffffff; --surface: #f8fafc; --surface2: #e2e8f0; --text: #0f172a; --text-muted: #475569; --border: #cbd5e1; --pass: #16a34a; --fail: #dc2626; --skip: #6b7280; --error: #d97706; --accent: #0284c7; }}
    body {{ background: #fff !important; color: #000 !important; }}
    .ext-body.collapsed {{ display: block !important; }}
    .ext-body {{ display: block !important; }}
    .ext-card {{ page-break-before: always; border: 1px solid #ccc !important; box-shadow: none !important; }}
    .summary-card, .breakdown, .theme-breakdown, .failure-panel, .cat-stat-card {{
        border: 1px solid #ccc !important;
        box-shadow: none !important;
    }}
    .result-pass {{ display: table-row !important; }}
}}
</style>
</head>
<body>
<a href="#main-content" class="skip-nav">Skip to main content</a>
<div class="layout">
<nav class="toc-nav" aria-label="Report navigation">
    <h2>Sections</h2>
    <a href="#summary">Summary</a>
    <a href="#categories">Categories</a>
    <a href="#languages">Languages</a>
    <a href="#themes">Themes</a>
    <a href="#failures">Failures</a>
    <a href="#extensions">Extensions</a>
</nav>
<div class="main-content" id="main-content">
    <div class="header">
        <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark/light mode">&#x1F319; Light</button>
        <h1>Anime Extensions Test Report</h1>
        <div class="meta">
            Run <code>{html_lib.escape(report.run_id)}</code> &middot;
            {html_lib.escape(report.repo_url)} (<code>{html_lib.escape(report.repo_commit)}</code>) &middot;
            {html_lib.escape(started)} &rarr; {html_lib.escape(finished)}
        </div>
    </div>

    <section id="summary" aria-label="Summary">
        <h2 class="section-heading">Summary</h2>
        <div class="hero">
            <div class="donut-wrap">{donut_svg}</div>
            <div class="donut-legend">
                <div class="donut-legend-item"><span class="donut-legend-dot" style="background:var(--pass)"></span> Passed: {summary.passed}</div>
                <div class="donut-legend-item"><span class="donut-legend-dot" style="background:var(--fail)"></span> Failed: {summary.failed}</div>
                <div class="donut-legend-item"><span class="donut-legend-dot" style="background:var(--skip)"></span> Skipped: {summary.skipped}</div>
                <div class="donut-legend-item"><span class="donut-legend-dot" style="background:var(--error)"></span> Errors: {summary.errors}</div>
            </div>
        </div>
        <div class="summary-grid">
            <div class="summary-card"><div class="value">{summary.total_extensions}</div>
                <div class="label">Extensions</div></div>
            <div class="summary-card pass"><div class="value">{summary.passed}</div>
                <div class="label">Passed</div></div>
            <div class="summary-card fail"><div class="value">{summary.failed}</div>
                <div class="label">Failed</div></div>
            <div class="summary-card skip"><div class="value">{summary.skipped}</div>
                <div class="label">Skipped</div></div>
            <div class="summary-card error"><div class="value">{summary.errors}</div>
                <div class="label">Errors</div></div>
            <div class="summary-card"><div class="value">{duration_str}</div>
                <div class="label">Duration</div></div>
        </div>
    </section>

    <section id="categories" aria-label="Category breakdown">
        <h2 class="section-heading">Categories</h2>
        <div class="cat-stats-row">{cat_cards}</div>
        <div class="breakdowns">
            <div class="breakdown">
                <h3>By Category</h3>
                <table>
                    <thead><tr><th>Category</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th></tr></thead>
                    <tbody>{cat_rows}</tbody>
                </table>
            </div>
            <div class="breakdown" id="languages">
                <h3>By Language</h3>
                <table>
                    <thead><tr><th>Lang</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th><th>Total</th></tr></thead>
                    <tbody>{lang_rows}</tbody>
                </table>
            </div>
        </div>
    </section>

    <section id="themes" aria-label="Theme breakdown">
        <h2 class="section-heading">Themes</h2>
        <div class="theme-breakdown">
            <h3>By Theme</h3>
            <table>
                <thead><tr><th>Theme</th><th>Extensions</th><th>Pass%</th><th>Fail%</th><th>Avg Health</th></tr></thead>
                <tbody>{theme_rows}</tbody>
            </table>
        </div>
    </section>

    <section id="failures" aria-label="Failure summary">
        <h2 class="section-heading">Failures</h2>
        <div class="failure-panel">
            <div class="failure-panel-header" onclick="toggleFailurePanel(this)" role="button" tabindex="0" aria-label="Toggle failure details" aria-expanded="false">
                <span>Failed / Error Extensions</span>
                <span class="collapse-arrow">&#x25B6;</span>
            </div>
            <div class="failure-panel-body" aria-expanded="false">{failure_items}</div>
        </div>
    </section>

    <div class="filters">
        <label>Search:</label>
        <input type="text" id="search-input" placeholder="Filter extensions..." oninput="filterExtensions()" aria-label="Filter extensions by name">
        <button class="filter-btn active" data-filter="all" onclick="setFilter(this,'all')" aria-label="Show all extensions">All</button>
        <button class="filter-btn" data-filter="failed" onclick="setFilter(this,'failed')" aria-label="Show failed extensions">Failed</button>
        <button class="filter-btn" data-filter="passed" onclick="setFilter(this,'passed')" aria-label="Show clean extensions">Clean</button>
        <label style="margin-left:auto">
            <input type="checkbox" id="show-pass-toggle" onchange="togglePassRows()"> Show passing tests
        </label>
    </div>

    <section id="extensions" aria-label="Extension results">
        <h2 class="section-heading">Extensions</h2>
        <div class="extensions" id="extensions-list">
            {ext_cards}
        </div>
    </section>

    <div class="footer">
        Generated by anime-extensions-testing &middot;
        {summary.total_tests} assertions across {summary.total_extensions} extensions
    </div>
</div>
</div>

<script>
function toggleCard(header) {{
    const body = header.nextElementSibling;
    const isCollapsed = body.classList.toggle('collapsed');
    header.setAttribute('aria-expanded', !isCollapsed);
    body.setAttribute('aria-expanded', !isCollapsed);
}}

function filterExtensions() {{
    const q = document.getElementById('search-input').value.toLowerCase();
    document.querySelectorAll('.ext-card').forEach(card => {{
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? '' : 'none';
    }});
}}

function setFilter(btn, filter) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.ext-card').forEach(card => {{
        const stats = card.querySelector('.ext-stats');
        const failCount = parseInt(stats.querySelector('.stat.fail').textContent) || 0;
        const passCount = parseInt(stats.querySelector('.stat.pass').textContent) || 0;
        if (filter === 'all') card.style.display = '';
        else if (filter === 'failed') card.style.display = failCount > 0 ? '' : 'none';
        else if (filter === 'passed') card.style.display = failCount === 0 ? '' : 'none';
    }});
}}

function togglePassRows() {{
    const show = document.getElementById('show-pass-toggle').checked;
    document.querySelectorAll('.result-pass').forEach(row => {{
        row.classList.toggle('show-pass', show);
    }});
}}

function toggleTheme() {{
    const html = document.documentElement;
    const isLight = html.classList.toggle('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    document.querySelector('.theme-toggle').innerHTML = isLight ? '&#x1F311; Dark' : '&#x1F319; Light';
}}

function toggleFailurePanel(header) {{
    const body = header.nextElementSibling;
    const isExpanded = body.classList.toggle('expanded');
    header.setAttribute('aria-expanded', isExpanded);
    body.setAttribute('aria-expanded', isExpanded);
    header.querySelector('.collapse-arrow').innerHTML = isExpanded ? '&#x25BC;' : '&#x25B6;';
}}

// Restore theme from localStorage
(function() {{
    const saved = localStorage.getItem('theme');
    if (saved === 'light') {{
        document.documentElement.classList.add('light-theme');
        const btn = document.querySelector('.theme-toggle');
        if (btn) btn.innerHTML = '&#x1F311; Dark';
    }}
}})();

// Keyboard support for clickable headers
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' || e.key === ' ') {{
        const el = document.activeElement;
        if (el && el.getAttribute('role') === 'button') {{
            e.preventDefault();
            el.click();
        }}
    }}
}});
</script>
</body>
</html>"""
