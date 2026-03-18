from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from robot.batch.reader import ReadStats
from robot.batch.worker import Provider, process
from robot.batch.writer import OutputWriter
from robot.domain import RUC, Status


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


def run(
    rucs: list[RUC],
    checkpoint: set[str],
    provider: Provider,
    writer: OutputWriter,
    concurrency: int,
    read_stats: ReadStats,
) -> Summary:
    summary = Summary(
        rows_read=read_stats.rows_read,
        valid=read_stats.valid,
        ignored=read_stats.ignored,
        duplicates=read_stats.duplicates,
    )
    pending = [r for r in rucs if str(r) not in checkpoint]
    summary.skipped = len(rucs) - len(pending)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(process, provider, ruc): ruc for ruc in pending}
        for future in as_completed(futures):
            result = future.result()
            summary.processed += 1
            if result.status == Status.OK:
                summary.succeeded += 1
            else:
                summary.failed += 1
            writer.write(result)

    return summary
