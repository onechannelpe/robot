from robot.domain import RUC, Status
from robot.batch.worker import process


class _OkProvider:
    def count_lines(self, ruc: RUC) -> int:
        return 42


class _FailingProvider:
    def count_lines(self, ruc: RUC) -> int:
        raise RuntimeError("network error")


def test_success():
    result = process(_OkProvider(), RUC("20100070970"))
    assert result.status == Status.OK
    assert result.registered_lines == 42

def test_failure_captured():
    result = process(_FailingProvider(), RUC("20100070970"))
    assert result.status == Status.FAILED
    assert result.error_code == "provider_error"
    assert "network error" in result.error_detail
