import pytest
from robot.domain import RUC, Result, Status


def test_valid_ruc():
    assert RUC("20100070970") == "20100070970"

def test_strips_whitespace():
    assert RUC("  20100070970  ") == "20100070970"

def test_too_short():
    with pytest.raises(ValueError):
        RUC("1234567890")

def test_too_long():
    with pytest.raises(ValueError):
        RUC("201000709701")

def test_non_digits():
    with pytest.raises(ValueError):
        RUC("2010007097X")

def test_result_defaults():
    r = Result(ruc=RUC("20100070970"))
    assert r.registered_lines == 0
    assert r.status == Status.OK
    assert r.error_code == ""
