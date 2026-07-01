"""HTML report writer — generate a self-contained, styled HTML report from RunReport."""

from __future__ import annotations

import html as html_lib
from pathlib import Path

from anime_ext_test.models import RunReport, RunSummary

_STATUS_ICONS = {"pass": "&#x2705;", "fail": "&#x274C;", "skip": "&#x23ED;", "error": "&#x26A0;"}
_STATUS_LABELS = {"pass": "Passed", "fail": "Failed", "skip": "Skipped", "error": "Error"}
_STATUS_COLORS = {"pass": "#22c55e", "fail": "#ef4444", "skip": "#6b7280", "error": "#f59e0b"}


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

    # Category breakdown rows
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

    # Language breakdown rows
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

    # Build extension cards
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

        # Build result rows for this extension
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
            <div class="ext-header" onclick="toggleCard(this)">
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
            <div class="ext-body collapsed">
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
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 1rem;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}

/* Header */
.header {{
    text-align: center;
    padding: 2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}}
.header h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; }}
.header .meta {{ color: var(--text-muted); font-size: 0.85rem; }}
.header .meta code {{ color: var(--accent); }}

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
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Anime Extensions Test Report</h1>
        <div class="meta">
            Run <code>{html_lib.escape(report.run_id)}</code> &middot;
            {html_lib.escape(report.repo_url)} (<code>{html_lib.escape(report.repo_commit)}</code>) &middot;
            {html_lib.escape(started)} &rarr; {html_lib.escape(finished)}
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
        <div class="summary-card"><div class="value">{summary.duration_seconds}s</div>
            <div class="label">Duration</div></div>
    </div>

    <div class="breakdowns">
        <div class="breakdown">
            <h3>By Category</h3>
            <table>
                <thead><tr><th>Category</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th></tr></thead>
                <tbody>{cat_rows}</tbody>
            </table>
        </div>
        <div class="breakdown">
            <h3>By Language</h3>
            <table>
                <thead><tr><th>Lang</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Error</th><th>Total</th></tr></thead>
                <tbody>{lang_rows}</tbody>
            </table>
        </div>
    </div>

    <div class="filters">
        <label>Search:</label>
        <input type="text" id="search-input" placeholder="Filter extensions..." oninput="filterExtensions()">
        <button class="filter-btn active" data-filter="all" onclick="setFilter(this,'all')">All</button>
        <button class="filter-btn" data-filter="failed" onclick="setFilter(this,'failed')">Failed</button>
        <button class="filter-btn" data-filter="passed" onclick="setFilter(this,'passed')">Clean</button>
        <label style="margin-left:auto">
            <input type="checkbox" id="show-pass-toggle" onchange="togglePassRows()"> Show passing tests
        </label>
    </div>

    <div class="extensions" id="extensions-list">
        {ext_cards}
    </div>

    <div class="footer">
        Generated by anime-extensions-testing &middot;
        {summary.total_tests} assertions across {summary.total_extensions} extensions
    </div>
</div>

<script>
function toggleCard(header) {{
    const body = header.nextElementSibling;
    body.classList.toggle('collapsed');
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
</script>
</body>
</html>"""
