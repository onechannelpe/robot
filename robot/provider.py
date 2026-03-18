from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from robot.domain import RUC


class LineCountProvider(Protocol, AbstractContextManager["LineCountProvider"]):
    def count_lines(self, ruc: RUC) -> int: ...

    def close(self) -> None: ...

    def __enter__(self) -> LineCountProvider:
        return self

    def __exit__(self, *_) -> None:
        self.close()
