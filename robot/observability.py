from __future__ import annotations

import logging
import sys
import time
import uuid

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator


def configure_logging(*, debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def new_session_id() -> str:
    return uuid.uuid4().hex[:10]


def kv(**fields: object) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


@dataclass
class OpTimer:
    _start: float
    _stop: float | None = None

    @property
    def elapsed_ms(self) -> int:
        end = self._stop if self._stop is not None else time.perf_counter()
        return int((end - self._start) * 1000)


@contextmanager
def timed() -> Iterator[OpTimer]:
    timer = OpTimer(_start=time.perf_counter())
    try:
        yield timer
    finally:
        timer._stop = time.perf_counter()
