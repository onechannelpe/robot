from robot.domain import RUC
from robot.osiptel.request import build_body


def test_ruc_and_token_present():
    body = build_body(RUC("20100070970"), "tok123", draw=1, start=0, length=100)
    assert body["models[NumeroDocumento]"] == "20100070970"
    assert body["models[ReCaptcha]"] == "tok123"
    assert body["models[GoogleCaptchaToken]"] == "tok123"
    assert body["models[GoogleCaptchaTokenOLD]"] == "tok123"

def test_pagination_fields():
    body = build_body(RUC("20100070970"), "", draw=3, start=200, length=50)
    assert body["draw"] == "3"
    assert body["start"] == "200"
    assert body["length"] == "50"

def test_all_columns_present():
    body = build_body(RUC("20100070970"), "", draw=1, start=0, length=100)
    assert body["columns[0][name]"] == "indice"
    assert body["columns[1][name]"] == "modalidad"
    assert body["columns[2][name]"] == "numeroservicio"
    assert body["columns[3][name]"] == "operador"
