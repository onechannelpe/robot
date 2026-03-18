import csv
from robot.domain import RUC, Result, Status
from robot.batch.writer import load_checkpoint, OutputWriter


def test_writes_header_once(tmp_path):
    p = tmp_path / "out.csv"
    with OutputWriter(p, "counts-only") as w:
        w.write(Result(ruc=RUC("20100070970"), registered_lines=5))
    with OutputWriter(p, "counts-only") as w:
        w.write(Result(ruc=RUC("20600000006"), registered_lines=2))
    rows = list(csv.reader(p.open()))
    assert rows[0] == ["ruc", "registered_lines"]
    assert len(rows) == 3

def test_counts_only_row(tmp_path):
    p = tmp_path / "out.csv"
    with OutputWriter(p, "counts-only") as w:
        w.write(Result(ruc=RUC("20100070970"), registered_lines=7))
    rows = list(csv.reader(p.open()))
    assert rows[1] == ["20100070970", "7"]

def test_detailed_row(tmp_path):
    p = tmp_path / "out.csv"
    with OutputWriter(p, "detailed") as w:
        w.write(Result(ruc=RUC("20100070970"), registered_lines=0,
                       status=Status.FAILED, error_code="provider_error", error_detail="timeout"))
    rows = list(csv.reader(p.open()))
    assert rows[1] == ["20100070970", "0", "failed", "provider_error", "timeout"]

def test_checkpoint_empty(tmp_path):
    assert load_checkpoint(tmp_path / "missing.csv") == set()

def test_checkpoint_reads_written_rucs(tmp_path):
    p = tmp_path / "out.csv"
    with OutputWriter(p, "counts-only") as w:
        w.write(Result(ruc=RUC("20100070970"), registered_lines=1))
    assert "20100070970" in load_checkpoint(p)
