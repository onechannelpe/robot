from robot.osiptel.provider import OsiptelProvider
from robot.proxy import GeonodeConfig


__all__ = [
    "GeonodeConfig",
    "OsiptelProvider",
    "build_osiptel_provider_from_env",
]


def build_osiptel_provider_from_env(
    *, page_size: int = 100, env_file: str = ".env"
) -> OsiptelProvider:
    return OsiptelProvider.from_env(page_size=page_size, env_file=env_file)
