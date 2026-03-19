from __future__ import annotations

import json
import logging
import operator
import time

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from selenium.common.exceptions import WebDriverException
from seleniumbase import SB  # type: ignore[import-untyped]

from robot.domain import RUC, CarrierLines
from robot.errors import (
    BanSignalError,
    CaptchaError,
    ParseError,
    TransientTransportError,
)
from robot.observability import kv, new_session_id, timed
from robot.osiptel.request import build_body


if TYPE_CHECKING:
    from robot.runtime.proxies import ProxyConfig


logger = logging.getLogger(__name__)

HOME_URL = "https://checatuslineas.osiptel.gob.pe/"
_IP_JSONP_URL = "https://api.ipify.org?format=jsonp"

_STATE_EXPR = """(() => ({
  ready: document.readyState || '',
  href: location.href || '',
  title: document.title || '',
  scripts: document.scripts ? document.scripts.length : -1,
  gc: typeof window.grecaptcha,
  key: (document.querySelector('#hiddenRecaptchaKey')||{}).value || ''
}))()"""

_TOKEN_START_EXPR = """(() => {
  window.__rcTok = '';
  window.__rcErr = '';
  const key = (document.querySelector('#hiddenRecaptchaKey') || {}).value || '';
  const action = (document.querySelector('#hiddenAction') || {}).value || '';
  if (!window.grecaptcha || !key) {
    window.__rcErr = 'missing grecaptcha or key';
    return false;
  }
  window.grecaptcha.ready(function() {
    window.grecaptcha.execute(key, {action: action})
      .then(tok => window.__rcTok = tok || '')
      .catch(err => window.__rcErr = String(err));
  });
  return true;
})()"""


@dataclass
class BrowserSettings:
    page_size: int
    chrome_binary: str = ""


class BrowserSession:
    def __init__(self, proxy: ProxyConfig, settings: BrowserSettings) -> None:
        self._proxy = proxy
        self._settings = settings
        self._session_id = new_session_id()
        self._sb_cm: SB | None = None
        self._sb: SB | None = None
        self.egress_ip: str = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def proxy_id(self) -> str:
        return self._proxy.proxy_id

    def open(self) -> None:
        kwargs: dict[str, Any] = {
            "uc": True,
            "headed": True,
            "xvfb": True,
            "proxy": self._proxy.as_selenium_proxy(self._session_id),
        }
        if self._settings.chrome_binary:
            kwargs["binary_location"] = self._settings.chrome_binary

        try:
            with timed() as timer:
                self._sb_cm = SB(**kwargs)
                self._sb = self._sb_cm.__enter__()
                self._sb.activate_cdp_mode(HOME_URL)
        except WebDriverException as exc:
            msg = f"failed to open browser session: {type(exc).__name__}: {exc}"
            raise TransientTransportError(msg) from exc
        logger.info(
            "session_open %s",
            kv(
                session_id=self._session_id,
                proxy_id=self._proxy.proxy_id,
                elapsed_ms=timer.elapsed_ms,
            ),
        )
        self._wait_ready()
        self.egress_ip = self._resolve_ip()
        logger.info(
            "session_ready %s",
            kv(
                session_id=self._session_id,
                proxy_id=self._proxy.proxy_id,
                egress_ip=self.egress_ip,
            ),
        )

    def close(self) -> None:
        if self._sb_cm is None:
            return
        try:
            self._sb_cm.__exit__(None, None, None)
        finally:
            self._sb_cm = None
            self._sb = None

    def count_lines(self, ruc: RUC) -> int:
        total, _ = self.count_carrier_lines(ruc)
        return total

    def count_carrier_lines(self, ruc: RUC) -> tuple[int, tuple[CarrierLines, ...]]:
        sb = self._require_sb()
        total: int | None = None
        start = 0
        draw = 2
        counts: dict[str, int] = {}

        while True:
            token = self._generate_recaptcha_token()
            payload = _fetch_page(
                sb,
                str(ruc),
                token,
                draw=draw,
                start=start,
                length=self._settings.page_size,
            )

            if total is None:
                total = int(payload.get("iTotalRecords", 0) or 0)

            rows = payload.get("aaData") or []
            _accumulate_carriers(counts, rows)
            logger.debug(
                "api_page %s",
                kv(
                    session_id=self._session_id,
                    proxy_id=self._proxy.proxy_id,
                    ruc=ruc,
                    draw=draw,
                    start=start,
                    rows=len(rows),
                    total=total,
                ),
            )

            if total == 0 or not rows:
                break

            start += len(rows)
            draw += 1
            if start >= total:
                break

        carrier_lines = tuple(
            CarrierLines(carrier=name, lines=lines)
            for name, lines in sorted(counts.items(), key=operator.itemgetter(0))
        )
        return total or 0, carrier_lines

    def _require_sb(self) -> SB:
        if self._sb is None:
            msg = "browser session not open"
            raise TransientTransportError(msg)
        return self._sb

    def _wait_ready(self, timeout_s: float = 25.0, poll_s: float = 0.25) -> None:
        sb = self._require_sb()
        deadline = time.monotonic() + timeout_s
        last_state: dict[str, Any] = {}
        with timed() as timer:
            while time.monotonic() < deadline:
                state = sb.execute_script(_STATE_EXPR) or {}
                if isinstance(state, dict):
                    last_state = state
                if (
                    state.get("scripts", 0) >= 20
                    and state.get("gc") == "object"
                    and state.get("key")
                ):
                    logger.info(
                        "session_wait_ready %s",
                        kv(session_id=self._session_id, elapsed_ms=timer.elapsed_ms),
                    )
                    return
                time.sleep(poll_s)
        msg = (
            "osiptel page not ready "
            f"ready={last_state.get('ready', '')} "
            f"href={last_state.get('href', '')} "
            f"title={last_state.get('title', '')} "
            f"scripts={last_state.get('scripts', '')} "
            f"gc={last_state.get('gc', '')} "
            f"has_key={bool(last_state.get('key'))}"
        )
        raise TransientTransportError(msg)

    def _generate_recaptcha_token(
        self, timeout_s: float = 20.0, poll_s: float = 0.25
    ) -> str:
        sb = self._require_sb()
        with timed() as timer:
            started = bool(sb.execute_script(_TOKEN_START_EXPR))
            if not started:
                msg = "failed to start recaptcha token generation"
                raise CaptchaError(msg)

            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                token = sb.execute_script("(() => window.__rcTok || '')()") or ""
                token_err = sb.execute_script("(() => window.__rcErr || '')()") or ""
                if isinstance(token, str) and token.strip():
                    logger.info(
                        "token_generated %s",
                        kv(
                            session_id=self._session_id,
                            proxy_id=self._proxy.proxy_id,
                            elapsed_ms=timer.elapsed_ms,
                            token_len=len(token.strip()),
                        ),
                    )
                    return token.strip()
                if token_err:
                    msg = f"captcha token generation failed: {token_err}"
                    raise CaptchaError(msg)
                time.sleep(poll_s)

        msg = "captcha token not generated in time"
        raise CaptchaError(msg)

    def _resolve_ip(self) -> str:
        sb = self._require_sb()
        start_expr = f"""(() => {{
  window.__ipVal = '';
  window.__ipErr = '';
  const cb = '__ipcb_' + Math.random().toString(36).slice(2);
  const script = document.createElement('script');
  function cleanup() {{
    try {{ delete window[cb]; }} catch (_) {{}}
    if (script.parentNode) {{
      script.parentNode.removeChild(script);
    }}
  }}
  window[cb] = function(payload) {{
    try {{
      window.__ipVal = (payload && payload.ip) ? String(payload.ip) : '';
    }} catch (_) {{
      window.__ipVal = '';
    }}
    cleanup();
  }};
  script.onerror = function() {{
    window.__ipErr = 'ip_jsonp_load_error';
    cleanup();
  }};
  script.src = '{_IP_JSONP_URL}&callback=' + cb;
  document.head.appendChild(script);
  return true;
}})()"""

        sb.execute_script(start_expr)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            ip_value = sb.execute_script("(() => window.__ipVal || '')()") or ""
            if isinstance(ip_value, str) and ip_value:
                return ip_value

            ip_err = sb.execute_script("(() => window.__ipErr || '')()") or ""
            if ip_err:
                return ""
            time.sleep(0.2)
        return ""


def _fetch_page(
    sb: SB, ruc: str, token: str, *, draw: int, start: int, length: int
) -> dict[str, Any]:
    body_json = json.dumps(
        build_body(RUC(ruc), token, draw=draw, start=start, length=length)
    )
    script = f"""(() => {{
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
}})()"""

    with timed() as timer:
        raw = sb.execute_script(script)

    if not isinstance(raw, str):
        msg = "osiptel request returned non-string payload"
        raise ParseError(msg)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = "osiptel request wrapper returned invalid json"
        raise ParseError(msg) from exc

    status = int(parsed.get("status", 0) or 0)
    body = parsed.get("body", "")

    logger.debug("api_fetch %s", kv(status=status, elapsed_ms=timer.elapsed_ms))

    if status >= 500:
        msg = f"osiptel request failed status={status}"
        raise BanSignalError(msg)
    if status != 200:
        msg = f"osiptel request failed status={status}"
        raise TransientTransportError(msg)
    if not isinstance(body, str) or not body.strip():
        msg = "osiptel response body empty"
        raise BanSignalError(msg)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        msg = "osiptel response is not valid json"
        raise ParseError(msg) from exc

    if not isinstance(payload, dict):
        msg = "osiptel response json is not an object"
        raise ParseError(msg)
    return payload


def _accumulate_carriers(counts: dict[str, int], rows: object) -> None:
    if not isinstance(rows, list):
        return
    for row in rows:
        carrier = _extract_carrier_name(row)
        counts[carrier] = counts.get(carrier, 0) + 1


def _extract_carrier_name(row: object) -> str:
    if isinstance(row, dict):
        value = row.get("operador")
        if isinstance(value, str):
            normalized = _normalize_carrier(value)
            if normalized:
                return normalized
        for key, value in row.items():
            if "operador" not in key.casefold():
                continue
            if isinstance(value, str):
                normalized = _normalize_carrier(value)
                if normalized:
                    return normalized
    if isinstance(row, list) and len(row) >= 4 and isinstance(row[3], str):
        normalized = _normalize_carrier(row[3])
        if normalized:
            return normalized
    return "unknown"


def _normalize_carrier(value: str) -> str:
    normalized = " ".join(value.strip().split())
    return normalized or "unknown"
