from __future__ import annotations

import time

from seleniumbase import SB

from robot.osiptel.session import HOME_URL


def solve(site_key: str) -> str:
    with SB(uc=True, headless=True) as sb:
        sb.open(HOME_URL)
        sb.uc_gui_click_captcha()
        return _wait_for_token(sb)


def _wait_for_token(sb: SB, timeout_s: float = 20.0, poll_s: float = 0.5) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        token = _extract_token(sb)
        if token:
            return token
        time.sleep(poll_s)
    msg = "captcha token not found after solving"
    raise RuntimeError(msg)


def _extract_token(sb: SB) -> str:
    script = """
(() => {
    const pickValue = (selector) => {
        const el = document.querySelector(selector);
        return el && typeof el.value === 'string' ? el.value.trim() : '';
    };
    return (
        pickValue('textarea[name="g-recaptcha-response"]') ||
        pickValue('input[name="g-recaptcha-response"]') ||
        pickValue('input[name="GoogleCaptchaToken"]') ||
        pickValue('input[id="GoogleCaptchaToken"]') ||
        pickValue('input[name="models.GoogleCaptchaToken"]')
    );
})();
"""
    token = sb.execute_script(script)
    return token.strip() if isinstance(token, str) else ""
