from __future__ import annotations

import os
import queue

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from robot.io.reader import enqueue_rucs
from robot.runtime.proxies import build_pool_from_env
from robot.runtime.summary import Summary, apply_worker_totals, from_read_stats
from robot.runtime.worker import Worker, WorkerSettings


if TYPE_CHECKING:
    from robot.config import Config
    from robot.domain import RUC
    from robot.io.writer import OutputWriter


def run_live(
    cfg: Config,
    writer: OutputWriter,
    *,
    checkpoint: set[str],
    run_id: str,
) -> Summary:
    proxy_pool = build_pool_from_env(env_file=cfg.env_file)
    worker_count = min(cfg.workers, len(proxy_pool.proxies))
    if worker_count < 1:
        return Summary()

    task_queue: queue.Queue[RUC | None] = queue.Queue(maxsize=worker_count * 100)
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
    if read_stats.enqueued == 0:
        return summary

    worker_count = min(worker_count, read_stats.enqueued)
    settings = WorkerSettings(
        page_size=cfg.page_size,
        session_budget=cfg.session_budget,
        wait_min_s=cfg.wait_min_s,
        wait_max_s=cfg.wait_max_s,
        same_session_retries=cfg.same_session_retries,
        ban_cooldown_s=cfg.ban_cooldown_s,
        chrome_binary=os.getenv("CHROME_BINARY", ""),
    )

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
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
            for idx in range(1, worker_count + 1)
        ]

        for _ in range(worker_count):
            task_queue.put(None)
        task_queue.join()

    worker_summaries = [future.result() for future in futures]
    return apply_worker_totals(summary, worker_summaries)
