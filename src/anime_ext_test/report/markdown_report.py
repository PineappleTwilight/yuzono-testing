"""Markdown report writer — generate human-readable Markdown from RunReport."""

from __future__ import annotations

from pathlib import Path

from anime_ext_test.models import RunReport, RunSummary


def write_markdown_report(report: RunReport, summary: RunSummary, output_dir: Path) -> Path:
    """Write a human-readable Markdown report. Returns the output path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"report-{report.run_id}.md"

    lines: list[str] = []
    lines.append("# Anime Extensions Test Report")
    lines.append("")
    lines.append(f"**Run ID:** `{report.run_id}`  ")
    lines.append(f"**Started:** {report.started_at.isoformat()}  ")
    lines.append(f"**Finished:** {report.finished_at.isoformat() if report.finished_at else 'N/A'}  ")
    lines.append(f"**Repo:** `{report.repo_url}` (`{report.repo_commit}`)  ")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Extensions tested | {summary.total_extensions} |")
    lines.append(f"| Total test assertions | {summary.total_tests} |")
    lines.append(f"| ✅ Passed | {summary.passed} |")
    lines.append(f"| ❌ Failed | {summary.failed} |")
    lines.append(f"| ⏭ Skipped | {summary.skipped} |")
    lines.append(f"| ⚠ Errors | {summary.errors} |")
    lines.append(f"| Duration | {summary.duration_seconds}s |")
    lines.append("")

    # By language
    if summary.by_language:
        lines.append("### By Language")
        lines.append("")
        lines.append("| Language | Passed | Failed | Skipped | Errors | Total |")
        lines.append("|----------|--------|--------|---------|--------|-------|")
        for lang in sorted(summary.by_language):
            s = summary.by_language[lang]
            lines.append(f"| {lang} | {s['passed']} | {s['failed']} | {s['skipped']} | {s['errors']} | {s['total']} |")
        lines.append("")

    # By test type
    if summary.by_test_type:
        lines.append("### By Test Category")
        lines.append("")
        lines.append("| Category | Passed | Failed | Skipped | Errors |")
        lines.append("|----------|--------|--------|---------|--------|")
        for cat in sorted(summary.by_test_type):
            s = summary.by_test_type[cat]
            lines.append(f"| {cat} | {s['passed']} | {s['failed']} | {s['skipped']} | {s['errors']} |")
        lines.append("")

    # Failed extensions (most actionable section)
    failed_exts = [er for er in report.extensions if er.failed > 0]
    if failed_exts:
        lines.append("## Failed Extensions")
        lines.append("")
        for er in sorted(failed_exts, key=lambda e: e.extension.module_id):
            lines.append(f"### `{er.extension.module_id}` — {er.extension.ext_name}")
            lines.append("")
            failed_results = [r for r in er.results if r.status == "fail"]
            for r in failed_results:
                detail = f" — `{r.detail}`" if r.detail else ""
                lines.append(f"- ❌ **{r.test_name}**: {r.message}{detail}")
            lines.append("")

    # Detailed per-extension results
    lines.append("## All Extensions")
    lines.append("")
    for er in sorted(report.extensions, key=lambda e: e.extension.module_id):
        ext = er.extension
        status_icon = "✅" if er.failed == 0 else "❌" if er.passed > 0 else "⚠️"
        lines.append(f"### {status_icon} `{ext.module_id}` — {ext.ext_name}")
        lines.append("")
        lines.append(f"- Lang: `{ext.lang}`  ")
        lines.append(f"- Theme: `{ext.theme_pkg or 'legacy'}`  ")
        lines.append(f"- baseUrl: `{ext.base_url or 'N/A'}`  ")
        lines.append(f"- NSFW: `{ext.is_nsfw}`  ")
        lines.append(f"- Results: {er.passed} pass / {er.failed} fail / {er.skipped} skip / {er.errored} error  ")
        lines.append("")
        for r in er.results:
            icon = {"pass": "✅", "fail": "❌", "skip": "⏭", "error": "⚠️"}.get(r.status, "?")
            detail = f" — `{r.detail}`" if r.detail and r.status in ("fail", "error") else ""
            lines.append(f"  - {icon} **{r.test_name}** ({r.duration_ms:.0f}ms): {r.message}{detail}")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return out_path
