from robot.batch.reader import read_rucs


def test_reads_valid_rucs(tmp_path):
    f = tmp_path / "in.csv"
    f.write_text("20100070970\n20600000006\n")
    rucs, stats = read_rucs(f)
    assert len(rucs) == 2
    assert stats.valid == 2
    assert stats.ignored == 0

def test_skips_invalid(tmp_path):
    f = tmp_path / "in.csv"
    f.write_text("NOTARUC\n\n20100070970\n")
    rucs, stats = read_rucs(f)
    assert len(rucs) == 1
    assert stats.ignored == 2

def test_deduplication(tmp_path):
    f = tmp_path / "in.csv"
    f.write_text("20100070970\n20100070970\n")
    rucs, stats = read_rucs(f, dedupe=True)
    assert len(rucs) == 1
    assert stats.duplicates == 1

def test_no_dedupe(tmp_path):
    f = tmp_path / "in.csv"
    f.write_text("20100070970\n20100070970\n")
    rucs, stats = read_rucs(f, dedupe=False)
    assert len(rucs) == 2
    assert stats.duplicates == 0

def test_strips_bom(tmp_path):
    f = tmp_path / "in.csv"
    f.write_bytes(b"\xef\xbb\xbf20100070970\n")
    rucs, _ = read_rucs(f)
    assert len(rucs) == 1
