from __future__ import annotations

import logging
from typing import Protocol

from robot.domain import Result, RUC, Status

logger = logging.getLogger(__name__)


class Provider(Protocol):
    def count_lines(self, ruc: RUC) -> int: ...


def process(provider: Provider, ruc: RUC) -> Result:
    try:
        count = provider.count_lines(ruc)
        logger.info("ok ruc=%s lines=%d", ruc, count)
        return Result(ruc=ruc, registered_lines=count, status=Status.OK)
    except Exception as exc:
        logger.error("failed ruc=%s err=%s", ruc, exc)
        return Result(ruc=ruc, status=Status.FAILED, error_code="provider_error", error_detail=str(exc))
