from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from v2.io.checkpoint import load_completed_rucs
from v2.io.writer import OutputWriter
from v2.obs.events import RUN_SUMMARY
from v2.obs.logging import kv
from v2.pipeline.dispatcher import run_dispatcher


if TYPE_CHECKING:
    from v2.app.config import RunConfig


logger = logging.getLogger(__name__)


def run(cfg: RunConfig, *, run_id: str) -> None:
    checkpoint = load_completed_rucs(cfg.output_csv)
    with OutputWriter(cfg.output_csv) as writer:
        summary = run_dispatcher(
            cfg,
            writer=writer,
            checkpoint=checkpoint,
            run_id=run_id,
        )

    logger.info(
        "%s %s",
        RUN_SUMMARY,
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
