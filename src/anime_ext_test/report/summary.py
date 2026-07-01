"""Summary computation — derive RunSummary from RunReport."""

from __future__ import annotations

from anime_ext_test.models import RunReport, RunSummary


def compute_summary(report: RunReport) -> RunSummary:
    """Compute aggregated statistics from a RunReport."""
    return RunSummary.from_report(report)
