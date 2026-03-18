from __future__ import annotations

import logging
import sys

from robot import config
from robot.batch.reader import read_rucs
from robot.batch.runner import run
from robot.batch.writer import load_checkpoint, OutputWriter
from robot.osiptel.provider import OsiptelProvider
from robot.snapshot.provider import SnapshotProvider


def main(argv: list[str] | None = None) -> None:
    cfg = config.load(argv)

    logging.basicConfig(
        level=logging.DEBUG if cfg.debug else logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )

    rucs, read_stats = read_rucs(cfg.input_csv, dedupe=cfg.dedupe)
    if not rucs:
        sys.exit("no valid RUCs in input")

    checkpoint = load_checkpoint(cfg.output_csv)
    provider = SnapshotProvider(cfg.snapshot_json) if cfg.use_snapshot else OsiptelProvider(cfg.page_size)

    with OutputWriter(cfg.output_csv, cfg.output_mode) as writer:
        summary = run(rucs, checkpoint, provider, writer, cfg.concurrency, read_stats)

    logging.info(
        "done rows_read=%d valid=%d ignored=%d duplicates=%d skipped=%d processed=%d ok=%d failed=%d",
        summary.rows_read, summary.valid, summary.ignored, summary.duplicates,
        summary.skipped, summary.processed, summary.succeeded, summary.failed,
    )
