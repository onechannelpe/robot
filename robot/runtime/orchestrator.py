from __future__ import annotations

import logging
import os
import queue

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from robot.domain import RUC, Result, Status
from robot.io.reader import enqueue_rucs
from robot.io.writer import OutputWriter, load_checkpoint
from robot.observability import kv, timed
from robot.runtime.proxies import build_pool_from_env
from robot.runtime.worker import Worker, WorkerSettings


if TYPE_CHECKING:
    from robot.config import Config


logger = logging.getLogger(__name__)


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


def run(cfg: Config, *, run_id: str) -> Summary:
    checkpoint = load_checkpoint(cfg.output_csv)
    with OutputWriter(cfg.output_csv) as writer:
        if cfg.use_snapshot:
            snapshot_summary = _run_snapshot(cfg, writer, checkpoint=checkpoint)
            summary = Summary(
                rows_read=snapshot_summary.rows_read,
                valid=snapshot_summary.valid,
                ignored=snapshot_summary.ignored,
                duplicates=snapshot_summary.duplicates,
                skipped=snapshot_summary.skipped,
            )
        else:
            snapshot_summary = _run_live(
                cfg, writer, checkpoint=checkpoint, run_id=run_id
            )
            summary = Summary(
                rows_read=snapshot_summary.rows_read,
                valid=snapshot_summary.valid,
                ignored=snapshot_summary.ignored,
                duplicates=snapshot_summary.duplicates,
                skipped=snapshot_summary.skipped,
            )

    summary.processed = snapshot_summary.processed
    summary.succeeded = snapshot_summary.succeeded
    summary.failed = snapshot_summary.failed

    logger.info(
        "run_summary %s",
        kv(
            run_id=run_id,
            rows_read=summary.rows_read,
            valid=summary.valid,
            ignored=summary.ignored,
            duplicates=summary.duplicates,
            skipped=summary.skipped,
            processed=summary.processed,
            succeeded=summary.succeeded,
            failed=summary.failed,
        ),
    )
    return summary


def _run_snapshot(
    cfg: Config,
    writer: OutputWriter,
    *,
    checkpoint: set[str],
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

    summary = Summary()
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
    summary.rows_read = read_stats.rows_read
    summary.valid = read_stats.valid
    summary.ignored = read_stats.ignored
    summary.duplicates = read_stats.duplicates
    summary.skipped = read_stats.skipped
    return summary


def _run_live(
    cfg: Config,
    writer: OutputWriter,
    *,
    checkpoint: set[str],
    run_id: str,
) -> Summary:
    proxy_pool = build_pool_from_env(env_file=cfg.env_file)
    workers = min(cfg.workers, len(proxy_pool.proxies))
    if workers < 1:
        return Summary()
    task_queue: queue.Queue[RUC | None] = queue.Queue(maxsize=workers * 100)

    read_stats = enqueue_rucs(
        cfg.input_csv,
        task_queue,
        dedupe=cfg.dedupe,
        checkpoint=checkpoint,
    )
    if read_stats.valid == 0:
        msg = "no valid RUCs in input"
        raise RuntimeError(msg)
    if read_stats.enqueued == 0:
        return Summary(
            rows_read=read_stats.rows_read,
            valid=read_stats.valid,
            ignored=read_stats.ignored,
            duplicates=read_stats.duplicates,
            skipped=read_stats.skipped,
        )

    workers = min(workers, read_stats.enqueued)

    settings = WorkerSettings(
        page_size=cfg.page_size,
        session_budget=cfg.session_budget,
        wait_min_s=cfg.wait_min_s,
        wait_max_s=cfg.wait_max_s,
        same_session_retries=cfg.same_session_retries,
        ban_cooldown_s=cfg.ban_cooldown_s,
        chrome_binary=os.getenv("CHROME_BINARY", ""),
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                Worker(
                    worker_id=idx,
                    run_id=run_id,
                    task_queue=task_queue,
                    proxy_pool=proxy_pool,
                    writer=writer,
                    settings=settings,
                ).run
            )
            for idx in range(1, workers + 1)
        ]
        for _ in range(workers):
            task_queue.put(None)
        task_queue.join()

    summary = Summary()
    for future in futures:
        worker_summary = future.result()
        summary.processed += worker_summary.processed
        summary.succeeded += worker_summary.succeeded
        summary.failed += worker_summary.failed
    summary.rows_read = read_stats.rows_read
    summary.valid = read_stats.valid
    summary.ignored = read_stats.ignored
    summary.duplicates = read_stats.duplicates
    summary.skipped = read_stats.skipped
    return summary
