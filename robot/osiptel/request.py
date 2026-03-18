from __future__ import annotations

from robot.domain import RUC

_COLUMNS = ["indice", "modalidad", "numeroservicio", "operador"]


def build_body(ruc: RUC, token: str, draw: int, start: int, length: int) -> dict[str, str]:
    body: dict[str, str] = {}
    for i, name in enumerate(_COLUMNS):
        body[f"columns[{i}][data]"] = str(i)
        body[f"columns[{i}][name]"] = name
        body[f"columns[{i}][searchable]"] = "false"
        body[f"columns[{i}][orderable]"] = "false"
        body[f"columns[{i}][search][value]"] = ""
        body[f"columns[{i}][search][regex]"] = "false"
    body.update({
        "order[0][column]": "0",
        "order[0][dir]": "asc",
        "draw": str(draw),
        "start": str(start),
        "length": str(length),
        "search[value]": "",
        "search[regex]": "false",
        "models[IdTipoDoc]": "2",
        "models[NumeroDocumento]": str(ruc),
        "models[Captcha]": "true",
        "models[ReCaptcha]": token,
        "models[GoogleCaptchaToken]": token,
        "models[GoogleCaptchaTokenOLD]": token,
    })
    return body
