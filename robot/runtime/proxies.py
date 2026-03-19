from __future__ import annotations

import time

from dataclasses import dataclass, field, replace
from os import getenv
from threading import Condition

from dotenv import load_dotenv

from robot.errors import TransientTransportError


_STICKY_HTTP_PORT_MIN = 10000
_STICKY_HTTP_PORT_MAX = 10900


@dataclass(frozen=True)
class ProxyConfig:
    proxy_id: str
    user: str
    password: str
    host: str = "proxy.geonode.io"
    port: str = "10000"
    proxy_type: str = ""
    country: str = ""
    state: str = ""
    city: str = ""
    asn: str = ""
    strict_off: bool = False
    lifetime: int = 10

    def with_session_username(self, session_id: str) -> str:
        base = f"{self.user}-type-{self.proxy_type}"
        if self.country:
            base += f"-country-{self.country}"
        if self.state:
            base += f"-state-{self.state}"
        if self.city:
            base += f"-city-{self.city}"
        if self.asn:
            base += f"-asn-{self.asn}"
        if self.strict_off:
            base += "-strict-off"
        base += f"-session-{session_id}"
        base += f"-lifetime-{self.lifetime}"
        return base

    def as_selenium_proxy(self, session_id: str) -> str:
        username = self.with_session_username(session_id)
        return f"{username}:{self.password}@{self.host}:{self.port}"


@dataclass(frozen=True)
class ProxyLease:
    proxy: ProxyConfig
    slot_id: int


@dataclass
class _SlotState:
    slot_id: int
    in_use: bool = False
    cooldown_until: float = 0.0


@dataclass
class ProxyPool:
    proxy: ProxyConfig
    capacity: int
    _states: list[_SlotState] = field(init=False)
    _cv: Condition = field(default_factory=Condition, init=False)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            msg = "proxy session capacity must be >= 1"
            raise ValueError(msg)
        self._states = [_SlotState(slot_id=i) for i in range(1, self.capacity + 1)]

    def acquire(self, *, wait_s: float = 30.0) -> ProxyLease:
        deadline = time.monotonic() + wait_s
        with self._cv:
            while True:
                now = time.monotonic()
                for state in self._states:
                    if state.in_use:
                        continue
                    if state.cooldown_until > now:
                        continue
                    state.in_use = True
                    lease_proxy = replace(
                        self.proxy,
                        proxy_id=f"{self.proxy.proxy_id}-slot-{state.slot_id}",
                    )
                    return ProxyLease(proxy=lease_proxy, slot_id=state.slot_id)
                remaining = deadline - now
                if remaining <= 0:
                    msg = "no sticky session slot available before timeout"
                    raise TransientTransportError(msg)
                self._cv.wait(timeout=remaining)

    def release(self, lease: ProxyLease, *, cooldown_s: float = 0.0) -> None:
        with self._cv:
            for state in self._states:
                if state.slot_id != lease.slot_id:
                    continue
                state.in_use = False
                if cooldown_s > 0:
                    state.cooldown_until = max(
                        state.cooldown_until,
                        time.monotonic() + cooldown_s,
                    )
                self._cv.notify_all()
                return

        msg = f"unknown sticky session slot {lease.slot_id}"
        raise RuntimeError(msg)


def build_pool_from_env(*, env_file: str = ".env", capacity: int) -> ProxyPool:
    load_dotenv(env_file, override=False)

    if getenv("GEONODE_PROXY_LIST", "").strip():
        msg = "GEONODE_PROXY_LIST is not supported in sticky-only mode"
        raise RuntimeError(msg)

    user = getenv("GEONODE_USER", "")
    password = getenv("GEONODE_PASS", "")
    host = getenv("GEONODE_HOST", "proxy.geonode.io")
    port = getenv("GEONODE_PORT", "10000")
    proxy_type = getenv("GEONODE_TYPE", "")
    country = getenv("GEONODE_COUNTRY", "")
    state = getenv("GEONODE_STATE", "")
    city = getenv("GEONODE_CITY", "")
    asn = getenv("GEONODE_ASN", "")
    strict_off = getenv("GEONODE_STRICT_OFF", "").lower() in {"1", "true", "yes"}
    lifetime_raw = getenv("GEONODE_LIFETIME", "").strip()
    lifetime = int(lifetime_raw) if lifetime_raw else 10

    if not user or not password:
        msg = "missing GEONODE_USER or GEONODE_PASS"
        raise RuntimeError(msg)
    if proxy_type not in {"residential", "datacenter", "mix"}:
        msg = "GEONODE_TYPE must be one of residential|datacenter|mix"
        raise RuntimeError(msg)

    try:
        port_num = int(port)
    except ValueError as exc:
        msg = "GEONODE_PORT must be a valid integer"
        raise RuntimeError(msg) from exc

    if not (_STICKY_HTTP_PORT_MIN <= port_num <= _STICKY_HTTP_PORT_MAX):
        msg = (
            "sticky-only mode requires GEONODE_PORT in 10000-10900 "
            f"(received {port_num})"
        )
        raise RuntimeError(msg)

    if lifetime < 3 or lifetime > 1440:
        msg = "GEONODE_LIFETIME must be between 3 and 1440 minutes"
        raise RuntimeError(msg)

    proxy = ProxyConfig(
        proxy_id="proxy-1",
        user=user,
        password=password,
        host=host,
        port=port,
        proxy_type=proxy_type,
        country=country,
        state=state,
        city=city,
        asn=asn,
        strict_off=strict_off,
        lifetime=lifetime,
    )
    return ProxyPool(proxy=proxy, capacity=capacity)
