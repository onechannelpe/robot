from __future__ import annotations

import logging
import uuid

from typing import TYPE_CHECKING

from robot.domain import RUC, Result, Status
from robot.observability import kv, timed


if TYPE_CHECKING:
    from robot.provider import LineCountProvider


logger = logging.getLogger(__name__)


def process(provider: LineCountProvider, ruc: RUC, *, run_id: str) -> Result:
    op_id = uuid.uuid4().hex[:8]
    try:
        with timed() as timer:
            count = provider.count_lines(ruc)
        logger.info(
            "lookup_ok %s",
            kv(
                run_id=run_id,
                op_id=op_id,
                ruc=ruc,
                lines=count,
                elapsed_ms=timer.elapsed_ms,
            ),
        )
        return Result(ruc=ruc, registered_lines=count, status=Status.OK)
    except Exception as exc:
        logger.exception(
            "lookup_failed %s",
            kv(
                run_id=run_id,
                op_id=op_id,
                ruc=ruc,
                error_code="provider_error",
            ),
        )
        return Result(
            ruc=ruc,
            status=Status.FAILED,
            error_code="provider_error",
            error_detail=str(exc),
        )
