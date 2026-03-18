from robot.domain import RUC, Status
from robot.batch.reader import ReadStats
from robot.batch.runner import run


class _StubProvider:
    def __init__(self, counts: dict[str, int]):
        self._counts = counts

    def count_lines(self, ruc: RUC) -> int:
        if str(ruc) not in self._counts:
            raise RuntimeError("not found")
        return self._counts[str(ruc)]


class _CollectingWriter:
    def __init__(self):
        self.written = []

    def write(self, result) -> None:
        self.written.append(result)


def _stats(**kwargs) -> ReadStats:
    s = ReadStats(rows_read=2, valid=2)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_all_succeed():
    rucs = [RUC("20100070970"), RUC("20600000006")]
    provider = _StubProvider({"20100070970": 5, "20600000006": 0})
    writer = _CollectingWriter()
    summary = run(rucs, set(), provider, writer, concurrency=1, read_stats=_stats())
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert len(writer.written) == 2

def test_checkpoint_skips_done():
    rucs = [RUC("20100070970"), RUC("20600000006")]
    provider = _StubProvider({"20600000006": 3})
    writer = _CollectingWriter()
    summary = run(rucs, {"20100070970"}, provider, writer, concurrency=1, read_stats=_stats())
    assert summary.skipped == 1
    assert summary.processed == 1
    assert writer.written[0].ruc == RUC("20600000006")

def test_provider_error_recorded():
    rucs = [RUC("20100070970")]
    provider = _StubProvider({})
    writer = _CollectingWriter()
    summary = run(rucs, set(), provider, writer, concurrency=1, read_stats=_stats())
    assert summary.failed == 1
    assert writer.written[0].status == Status.FAILED
