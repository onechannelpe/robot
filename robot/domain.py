from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_RUC_RE = re.compile(r"^\d{11}$")


class RUC(str):
    def __new__(cls, value: str) -> "RUC":
        v = value.strip()
        if not _RUC_RE.match(v):
            raise ValueError(f"invalid RUC {value!r}: must be 11 digits")
        return super().__new__(cls, v)


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
