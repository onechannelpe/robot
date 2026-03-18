from __future__ import annotations

import httpx

from robot.domain import RUC
from robot.osiptel import captcha, fetch, session


class OsiptelProvider:
    def __init__(self, page_size: int = 100) -> None:
        self._page_size = page_size
        self._client = httpx.Client(timeout=30)

    def count_lines(self, ruc: RUC) -> int:
        sess = session.acquire(self._client)
        token = captcha.solve(sess.site_key)
        return fetch.count_lines(self._client, sess, ruc, token, self._page_size)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OsiptelProvider":
        return self

    def __exit__(self, *_) -> None:
        self.close()
