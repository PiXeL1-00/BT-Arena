"""Debug entry-point -- run with hot-reload and optional debugpy attach.

  python debug.py              # normal debug run
  python debug.py --wait       # pause until remote debugger attaches
  python debug.py --port 5679  # custom debugpy port
"""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("LOG_LEVEL", "DEBUG")

from app.infra.logging_config import ShortPathFormatter, configure_logging

formatter = ShortPathFormatter(
    "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
)
configure_logging(formatter)

logger = logging.getLogger("debug")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Galileo Arena – debug server")
    default_port = int(os.environ.get("PORT", "8000"))
    p.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=default_port, help="Uvicorn port (default: 8000, or PORT env var)")
    p.add_argument("--debugpy-port", type=int, default=5678)
    p.add_argument("--wait", action="store_true", help="Wait for debugger attach")
    p.add_argument("--no-reload", action="store_true")
    return p.parse_args()


def _attach_debugpy(*, port: int, wait: bool) -> None:
    try:
        import debugpy  # type: ignore
    except ImportError:
        logger.warning("debugpy not installed, skipping. pip install debugpy")
        return

    try:
        debugpy.listen(("0.0.0.0", port))
        # tiny delay so the port is definitely bound before compound-launch attach kicks in
        time.sleep(0.1)

        # readiness file for preLaunchTask synchronisation
        try:
            ready = Path(tempfile.gettempdir()) / f"debugpy_ready_{port}.txt"
            ready.write_text(f"{os.getpid()}\n{port}\n{time.time()}\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("couldn't write readiness file: %s", exc)

        logger.info("debugpy on 0.0.0.0:%s  wait=%s  pid=%s", port, wait, os.getpid())
    except Exception as exc:
        if "already listening" in str(exc).lower() or "address already in use" in str(exc).lower():
            logger.debug("debugpy already up on :%s (pid %s)", port, os.getpid())
        else:
            logger.warning("debugpy listen failed (pid %s): %s", os.getpid(), exc)
            return

    if wait:
        logger.info("Waiting for debugger attach …")
        debugpy.wait_for_client()
        logger.info("Debugger attached, resuming.")
    else:
        logger.info("Attach with 'Python: FastAPI (Attach to debugpy)' when ready.")


def main() -> None:
    args = _parse_args()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    _attach_debugpy(port=args.debugpy_port, wait=args.wait)

    import uvicorn  # type: ignore[import-untyped]

    use_reload = not args.no_reload
    logger.info("Starting Galileo Arena  host=%s  port=%s  reload=%s", args.host, args.port, use_reload)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=use_reload,
        log_level="debug",
        log_config=None,
    )


if __name__ == "__main__":
    main()
