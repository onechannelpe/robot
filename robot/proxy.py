from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class GeonodeConfig:
    user: str = ""
    password: str = ""
    host: str = "proxy.geonode.io"
    port: str = "9000"
    proxy_type: str = ""
    country: str = ""

    @classmethod
    def from_env(cls, *, env_file: str = ".env") -> GeonodeConfig:
        # Keep package usage simple: loading .env is best effort and non-fatal.
        load_dotenv(env_file, override=False)
        return cls(
            user=getenv("GEONODE_USER", ""),
            password=getenv("GEONODE_PASS", ""),
            host=getenv("GEONODE_HOST", "proxy.geonode.io"),
            port=getenv("GEONODE_PORT", "9000"),
            proxy_type=getenv("GEONODE_TYPE", ""),
            country=getenv("GEONODE_COUNTRY", ""),
        )

    def is_set(self) -> bool:
        return all([self.user, self.password, self.host, self.port])

    def validate(self) -> None:
        if not self.is_set():
            return
        if self.proxy_type not in {"residential", "datacenter", "mix"}:
            msg = "GEONODE_TYPE must be one of residential|datacenter|mix when proxy credentials are set"
            raise ValueError(msg)

    def _username(self) -> str:
        username = f"{self.user}-type-{self.proxy_type}"
        if self.country:
            username += f"-country-{self.country}"
        return username

    def as_http_url(self) -> str:
        self.validate()
        if not self.is_set():
            return ""
        return f"http://{self._username()}:{self.password}@{self.host}:{self.port}"

    def as_selenium_proxy(self) -> str:
        self.validate()
        if not self.is_set():
            return ""
        return f"{self._username()}:{self.password}@{self.host}:{self.port}"
