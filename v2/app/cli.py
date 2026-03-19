from __future__ import annotations

import logging

from v2.app.config import load_config
from v2.app.run import run
from v2.obs.events import RUN_START
from v2.obs.logging import configure_logging, kv, new_run_id


def main(argv: list[str] | None = None) -> None:
    cfg = load_config(argv)
    run_id = new_run_id()

    configure_logging(debug=cfg.debug)
    logging.getLogger(__name__).info("%s %s", RUN_START, kv(run_id=run_id))

    run(cfg, run_id=run_id)


if __name__ == "__main__":
    main()
