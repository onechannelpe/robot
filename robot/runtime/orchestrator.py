from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from robot.io.writer import OutputWriter, load_checkpoint
from robot.observability import kv
from robot.runtime.live_runner import run_live
from robot.runtime.snapshot_runner import run_snapshot


if TYPE_CHECKING:
    from robot.config import Config
    from robot.runtime.summary import Summary


logger = logging.getLogger(__name__)


def run(cfg: Config, *, run_id: str) -> Summary:
    checkpoint = load_checkpoint(cfg.output_csv)

    with OutputWriter(cfg.output_csv) as writer:
        if cfg.use_snapshot:
            summary = run_snapshot(
                cfg,
                writer,
                checkpoint=checkpoint,
                logger=logger,
            )
        else:
            summary = run_live(
                cfg,
                writer,
                checkpoint=checkpoint,
                run_id=run_id,
            )

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
