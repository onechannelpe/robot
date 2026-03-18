import json
from robot.domain import RUC
from robot.snapshot.provider import SnapshotProvider


def test_known_ruc(tmp_path):
    p = tmp_path / "snap.json"
    p.write_text(json.dumps({"20100070970": 42}))
    assert SnapshotProvider(p).count_lines(RUC("20100070970")) == 42

def test_unknown_ruc_returns_zero(tmp_path):
    p = tmp_path / "snap.json"
    p.write_text("{}")
    assert SnapshotProvider(p).count_lines(RUC("20100070970")) == 0
