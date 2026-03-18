from __future__ import annotations

from seleniumbase import SB

from robot.osiptel.session import HOME_URL


def solve(site_key: str) -> str:
    with SB(uc=True, headless=True) as sb:
        sb.open(HOME_URL)
        sb.uc_gui_click_captcha()
        return sb.get_google_auth_token(site_key)
