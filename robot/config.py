from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    input_csv: Path
    output_csv: Path
    output_mode: str
    page_size: int
    concurrency: int
    dedupe: bool
    debug: bool
    use_snapshot: bool
    snapshot_json: Path | None


def load(argv: list[str] | None = None) -> Config:
    p = argparse.ArgumentParser(prog="robot")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--output-mode", default="counts-only", choices=["counts-only", "detailed"])
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=1)
    p.add_argument("--dedupe", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--debug", action="store_true", default=False)
    p.add_argument("--snapshot-mode", action="store_true", default=False)
    p.add_argument("--snapshot", type=Path, default=None)
    ns = p.parse_args(argv)

    errors = []
    if ns.page_size < 1:
        errors.append("--page-size must be >= 1")
    if ns.concurrency < 1:
        errors.append("--concurrency must be >= 1")
    if ns.snapshot_mode and not ns.snapshot:
        errors.append("--snapshot required with --snapshot-mode")
    if errors:
        p.error("; ".join(errors))

    return Config(
        input_csv=ns.input,
        output_csv=ns.output,
        output_mode=ns.output_mode,
        page_size=ns.page_size,
        concurrency=ns.concurrency,
        dedupe=ns.dedupe,
        debug=ns.debug,
        use_snapshot=ns.snapshot_mode,
        snapshot_json=ns.snapshot,
    )
