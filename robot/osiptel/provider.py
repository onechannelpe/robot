from __future__ import annotations

import json
import logging
import time
from typing import Any

from seleniumbase import SB  # type: ignore[import-untyped]

from robot.domain import RUC
from robot.observability import kv
from robot.osiptel.request import build_body
from robot.osiptel.session import HOME_URL
from robot.proxy import GeonodeConfig


logger = logging.getLogger(__name__)

_STATE_EXPR = """(() => ({
  scripts: document.scripts ? document.scripts.length : -1,
  gc: typeof window.grecaptcha,
  key: (document.querySelector('#hiddenRecaptchaKey')||{}).value || '',
  action: (document.querySelector('#hiddenAction')||{}).value || ''
}))()"""

_TOKEN_START_EXPR = """(() => {
  window.__rcTok = '';
  window.__rcErr = '';
  const cs = (document.querySelector('#hiddenRecaptchaKey') || {}).value || '';
  const action = (document.querySelector('#hiddenAction') || {}).value || '';
  if (!window.grecaptcha || !cs) {
    window.__rcErr = 'missing grecaptcha or key';
    return false;
  }
  window.grecaptcha.ready(function() {
    window.grecaptcha.execute(cs, {action: action})
      .then(tok => window.__rcTok = tok || '')
      .catch(err => window.__rcErr = String(err));
  });
  return true;
})()"""


class OsiptelProvider:
    def __init__(self, page_size: int = 100, *, proxy: str = "") -> None:
        self._page_size = page_size
        self._proxy = proxy
        self._sb_cm: SB | None = None
        self._sb: SB | None = None

    @classmethod
    def from_env(
        cls, page_size: int = 100, *, env_file: str = ".env"
    ) -> OsiptelProvider:
        geonode = GeonodeConfig.from_env(env_file=env_file)
        return cls(page_size=page_size, proxy=geonode.as_selenium_proxy())

    def count_lines(self, ruc: RUC) -> int:
        try:
            return self._count_lines_once(ruc)
        except Exception as exc:
            if not _is_driver_disconnect(exc):
                raise
            logger.warning(
                "driver_disconnect_retry %s", kv(ruc=ruc, err=type(exc).__name__)
            )
            self.close()
            return self._count_lines_once(ruc)

    def _count_lines_once(self, ruc: RUC) -> int:
        sb = self._ensure_session()
        _wait_for_app_ready(sb)
        return _count_total_via_paginated_api(sb, str(ruc), page_size=self._page_size)

    def _ensure_session(self) -> SB:
        if self._sb is not None:
            return self._sb

        kwargs: dict[str, Any] = {"uc": True, "headed": True, "xvfb": True}
        if self._proxy:
            kwargs["proxy"] = self._proxy

        self._sb_cm = SB(**kwargs)
        self._sb = self._sb_cm.__enter__()
        self._sb.activate_cdp_mode(HOME_URL)
        return self._sb

    def close(self) -> None:
        if self._sb_cm is not None:
            try:
                self._sb_cm.__exit__(None, None, None)
            finally:
                self._sb_cm = None
                self._sb = None

    def __enter__(self) -> OsiptelProvider:
        return self

    def __exit__(self, *_) -> None:
        self.close()


def _wait_for_app_ready(sb: SB, timeout_s: float = 25.0, poll_s: float = 0.25) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = sb.execute_script(_STATE_EXPR) or {}
        if (
            state.get("scripts", 0) >= 20
            and state.get("gc") == "object"
            and state.get("key")
        ):
            return
        time.sleep(poll_s)
    msg = "osiptel page not ready"
    raise RuntimeError(msg)


def _generate_recaptcha_token(
    sb: SB, timeout_s: float = 20.0, poll_s: float = 0.25
) -> str:
    started = bool(sb.execute_script(_TOKEN_START_EXPR))
    if not started:
        msg = "failed to start recaptcha token generation"
        raise RuntimeError(msg)

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        token = sb.execute_script("(() => window.__rcTok || '')()") or ""
        token_err = sb.execute_script("(() => window.__rcErr || '')()") or ""
        if isinstance(token, str) and token.strip():
            return token.strip()
        if token_err:
            msg = f"captcha token generation failed: {token_err}"
            raise RuntimeError(msg)
        time.sleep(poll_s)

    msg = "captcha token not generated in time"
    raise RuntimeError(msg)


def _count_total_via_paginated_api(sb: SB, ruc: str, *, page_size: int) -> int:
    total: int | None = None
    start = 0
    draw = 2

    while True:
        # Keep token and request in the same browser session/context for each page call.
        token = _generate_recaptcha_token(sb)
        payload = _fetch_page(sb, ruc, token, draw=draw, start=start, length=page_size)

        if total is None:
            total = int(payload.get("iTotalRecords", 0) or 0)

        rows = payload.get("aaData") or []
        logger.debug(
            "api_page %s",
            kv(ruc=ruc, draw=draw, start=start, rows=len(rows), total=total),
        )

        if total == 0 or not rows:
            break

        start += len(rows)
        draw += 1
        if start >= total:
            break

    return total or 0


def _fetch_page(
    sb: SB, ruc: str, token: str, *, draw: int, start: int, length: int
) -> dict:
    body_json = json.dumps(
        build_body(RUC(ruc), token, draw=draw, start=start, length=length)
    )
    script = f"""
return (() => {{
  const data = {body_json};
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(data)) {{
    params.append(k, v);
  }}
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/Consultas/GetAllCabeceraConsulta/', false);
  xhr.setRequestHeader('Accept', '*/*');
  xhr.setRequestHeader('Cache-Control', 'no-cache');
  xhr.setRequestHeader('Pragma', 'no-cache');
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
  xhr.send(params.toString());
  return JSON.stringify({{ status: xhr.status, body: xhr.responseText || '' }});
}})();
"""
    raw = sb.execute_script(script)
    parsed = json.loads(raw) if isinstance(raw, str) else {}
    status = int(parsed.get("status", 0) or 0)
    body = parsed.get("body", "")
    if status != 200:
        msg = f"osiptel request failed status={status}"
        raise RuntimeError(msg)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        msg = "osiptel response is not valid json"
        raise RuntimeError(msg) from exc


def _is_driver_disconnect(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "connection refused" in text
        or "max retries exceeded" in text
        or "invalid session id" in text
        or "chrome not reachable" in text
    )
