from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from robot.io.reader import ReadStats
    from robot.runtime.worker import WorkerSummary


@dataclass
class Summary:
    rows_read: int = 0
    valid: int = 0
    ignored: int = 0
    duplicates: int = 0
    skipped: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0


def from_read_stats(stats: ReadStats) -> Summary:
    return Summary(
        rows_read=stats.rows_read,
        valid=stats.valid,
        ignored=stats.ignored,
        duplicates=stats.duplicates,
        skipped=stats.skipped,
    )


def apply_worker_totals(
    summary: Summary, worker_summaries: list[WorkerSummary]
) -> Summary:
    for worker_summary in worker_summaries:
        summary.processed += worker_summary.processed
        summary.succeeded += worker_summary.succeeded
        summary.failed += worker_summary.failed
    return summary
