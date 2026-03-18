from __future__ import annotations

import re

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import httpx


HOME_URL = "https://checatuslineas.osiptel.gob.pe/"
_COOKIE_SESSION_PREFIX = "cookiesession1"
_COOKIE_ANTIFORGERY_PREFIX = ".AspNetCore.Antiforgery"
_FALLBACK_SITE_KEY = "6LdcxV8dAAAAAMQZV05VmMp5TYlQJGoGQjv6FgX8"


@dataclass
class Session:
    cookie: str
    site_key: str


def acquire(client: httpx.Client) -> Session:
    resp = client.get(HOME_URL)
    resp.raise_for_status()

    # Cookies may be available either on the response jar or already merged into
    # the client jar, and the antiforgery suffix can change across deployments.
    cookies = {c.name: c.value for c in resp.cookies.jar}
    cookies.update({c.name: c.value for c in client.cookies.jar})

    session_name, session_val = _find_cookie(cookies, _COOKIE_SESSION_PREFIX)
    antiforgery_name, antiforgery_val = _find_cookie(
        cookies, _COOKIE_ANTIFORGERY_PREFIX
    )
    if (
        not session_name
        or not session_val
        or not antiforgery_name
        or not antiforgery_val
    ):
        msg = f"missing session cookies (got: {list(cookies)})"
        raise RuntimeError(msg)

    return Session(
        cookie=f"{session_name}={session_val}; {antiforgery_name}={antiforgery_val}",
        site_key=_extract_site_key(resp.text) or _FALLBACK_SITE_KEY,
    )


def _find_cookie(cookies: dict[str, str], name_prefix: str) -> tuple[str, str]:
    for name, value in cookies.items():
        if name.startswith(name_prefix):
            return name, value
    return "", ""


def _extract_site_key(html: str) -> str:
    m = re.search(r'data-sitekey=[\'"](\S+)[\'"]', html)
    return m.group(1) if m else ""
