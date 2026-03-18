from __future__ import annotations

import csv
import threading
from pathlib import Path

from robot.domain import Result

_HEADERS = {
    "counts-only": ["ruc", "registered_lines"],
    "detailed":    ["ruc", "registered_lines", "status", "error_code", "error_detail"],
}


def load_checkpoint(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return {row[0] for row in rows[1:] if row}


class OutputWriter:
    def __init__(self, path: Path, mode: str) -> None:
        if mode not in _HEADERS:
            raise ValueError(f"unknown output mode {mode!r}")
        self._mode = mode
        self._lock = threading.Lock()
        is_new = not path.exists() or path.stat().st_size == 0
        self._f = path.open("a", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        if is_new:
            self._w.writerow(_HEADERS[mode])
            self._f.flush()

    def write(self, result: Result) -> None:
        if self._mode == "detailed":
            row = [result.ruc, result.registered_lines, result.status.value, result.error_code, result.error_detail]
        else:
            row = [result.ruc, result.registered_lines]
        with self._lock:
            self._w.writerow(row)
            self._f.flush()

    def close(self) -> None:
        with self._lock:
            self._f.close()

    def __enter__(self) -> "OutputWriter":
        return self

    def __exit__(self, *_) -> None:
        self.close()
