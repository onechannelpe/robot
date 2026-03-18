from __future__ import annotations

import json

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from robot.domain import RUC


class SnapshotProvider:
    def __init__(self, path: Path) -> None:
        self._counts: dict[str, int] = json.loads(path.read_text())

    def count_lines(self, ruc: RUC) -> int:
        return self._counts.get(str(ruc), 0)

    def close(self) -> None:
        return None

    def __enter__(self) -> SnapshotProvider:
        return self

    def __exit__(self, *_) -> None:
        self.close()
