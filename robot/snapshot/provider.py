from __future__ import annotations

import json
from pathlib import Path

from robot.domain import RUC


class SnapshotProvider:
    def __init__(self, path: Path) -> None:
        self._counts: dict[str, int] = json.loads(path.read_text())

    def count_lines(self, ruc: RUC) -> int:
        return self._counts.get(str(ruc), 0)
