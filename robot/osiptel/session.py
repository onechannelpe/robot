from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

HOME_URL = "https://checatuslineas.osiptel.gob.pe/"
_COOKIE_SESSION = "cookiesession1"
_COOKIE_ANTIFORGERY = ".AspNetCore.Antiforgery.7wgomjq1Fus"
_FALLBACK_SITE_KEY = "6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8"


@dataclass
class Session:
    cookie: str
    site_key: str


def acquire(client: httpx.Client) -> Session:
    resp = client.get(HOME_URL)
    resp.raise_for_status()
    cookies = {c.name: c.value for c in resp.cookies.jar}
    session_val = cookies.get(_COOKIE_SESSION, "")
    antiforgery_val = cookies.get(_COOKIE_ANTIFORGERY, "")
    if not session_val or not antiforgery_val:
        raise RuntimeError(f"missing session cookies (got: {list(cookies)})")
    return Session(
        cookie=f"{_COOKIE_SESSION}={session_val}; {_COOKIE_ANTIFORGERY}={antiforgery_val}",
        site_key=_extract_site_key(resp.text) or _FALLBACK_SITE_KEY,
    )


def _extract_site_key(html: str) -> str:
    m = re.search(r'data-sitekey=[\'"](\S+)[\'"]', html)
    return m.group(1) if m else ""
