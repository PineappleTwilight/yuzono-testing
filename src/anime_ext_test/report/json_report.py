"""JSON report writer — serialize RunReport to JSON."""

from __future__ import annotations

import json
from pathlib import Path

from anime_ext_test.models import RunReport, RunSummary


def write_json_report(report: RunReport, output_dir: Path) -> Path:
    """Write the full RunReport as a JSON file. Returns the output path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"report-{report.run_id}.json"

    data = json.loads(report.model_dump_json())
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return out_path


def write_summary_json(summary: RunSummary, report: RunReport, output_dir: Path) -> Path:
    """Write the RunSummary as a JSON file. Returns the output path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"summary-{report.run_id}.json"

    data = json.loads(summary.model_dump_json())
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return out_path
