from __future__ import annotations

import queue

from typing import TYPE_CHECKING

from robot.domain import RUC, Result, Status
from robot.io.reader import enqueue_rucs
from robot.observability import kv, timed
from robot.runtime.summary import Summary, from_read_stats


if TYPE_CHECKING:
    import logging

    from robot.config import Config
    from robot.io.writer import OutputWriter


def run_snapshot(
    cfg: Config,
    writer: OutputWriter,
    *,
    checkpoint: set[str],
    logger: logging.Logger,
) -> Summary:
    from robot.snapshot.provider import SnapshotProvider

    if cfg.snapshot_json is None:
        msg = "snapshot_json is required in snapshot mode"
        raise RuntimeError(msg)

    task_queue: queue.Queue[RUC | None] = queue.Queue()
    read_stats = enqueue_rucs(
        cfg.input_csv,
        task_queue,
        dedupe=cfg.dedupe,
        checkpoint=checkpoint,
    )
    if read_stats.valid == 0:
        msg = "no valid RUCs in input"
        raise RuntimeError(msg)

    summary = from_read_stats(read_stats)
    provider = SnapshotProvider(cfg.snapshot_json)
    with provider:
        while True:
            try:
                ruc = task_queue.get_nowait()
            except queue.Empty:
                break
            if ruc is None:
                continue
            with timed() as timer:
                lines = provider.count_lines(ruc)
            writer.write(Result(ruc=ruc, total_lines=lines, status=Status.OK))
            summary.processed += 1
            summary.succeeded += 1
            logger.info(
                "snapshot_lookup_ok %s",
                kv(ruc=ruc, lines=lines, elapsed_ms=timer.elapsed_ms),
            )

    return summary
