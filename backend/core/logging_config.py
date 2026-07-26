"""
Logging setup.

The codebase used bare ``print()`` calls throughout, which means output has no
level, no timestamp, no module attribution, and cannot be filtered or captured
by a log aggregator. Worse, in the PyInstaller build there is no attached
console on Windows, so those prints go nowhere at all.

``configure_logging`` installs a single stream handler on the root logger and
aligns uvicorn's loggers with it so the output is consistent.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_configured = False


def configure_logging(level: str = "INFO", *, force: bool = False) -> None:
    """
    Configure root logging once per process.

    Args:
        level: Log level name (``DEBUG``, ``INFO``, ...).
        force: Reconfigure even if logging was already set up.
    """
    global _configured
    if _configured and not force:
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn installs its own handlers; make them defer to ours so the output
    # is not duplicated with a different format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    # These libraries are extremely chatty at DEBUG and drown out our own logs.
    for name in ("httpx", "httpcore", "urllib3", "matplotlib", "PIL", "rasterio"):
        logging.getLogger(name).setLevel(max(logging.INFO, logging.getLevelName(level)))

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
