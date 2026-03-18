from __future__ import annotations

import re

from collections import UserString
from dataclasses import dataclass
from enum import Enum


_RUC_RE = re.compile(r"^\d{11}$")


class RUC(UserString):
    def __init__(self, value: str) -> None:
        v = value.strip()
        if not _RUC_RE.match(v):
            msg = f"invalid RUC {value!r}: must be 11 digits"
            raise ValueError(msg)
        super().__init__(v)


class Status(str, Enum):
    OK = "ok"
    FAILED = "failed"


@dataclass
class Result:
    ruc: RUC
    registered_lines: int = 0
    status: Status = Status.OK
    error_code: str = ""
    error_detail: str = ""
