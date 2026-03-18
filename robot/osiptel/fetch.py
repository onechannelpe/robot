from __future__ import annotations

import httpx

from robot.domain import RUC
from robot.osiptel.request import build_body
from robot.osiptel.session import Session

_API_URL = "https://checatuslineas.osiptel.gob.pe/Consultas/GetAllCabeceraConsulta/"


def count_lines(client: httpx.Client, session: Session, ruc: RUC, token: str, page_size: int) -> int:
    total = None
    start = 0
    draw = 1
    while True:
        page = _fetch_page(client, session, ruc, token, draw, start, page_size)
        if total is None:
            total = page["iTotalRecords"]
        if total == 0 or not page["aaData"]:
            break
        start += len(page["aaData"])
        draw += 1
        if start >= total:
            break
    return total or 0


def _fetch_page(client: httpx.Client, session: Session, ruc: RUC, token: str, draw: int, start: int, length: int) -> dict:
    resp = client.post(
        _API_URL,
        data=build_body(ruc, token, draw, start, length),
        headers=_headers(session.cookie),
    )
    resp.raise_for_status()
    return resp.json()


def _headers(cookie: str) -> dict[str, str]:
    return {
        "Accept": "*/*",
        "Accept-Language": "en,es;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie,
        "Pragma": "no-cache",
        "Referer": "https://checatuslineas.osiptel.gob.pe/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
