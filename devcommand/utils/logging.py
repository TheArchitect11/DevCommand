"""Structured logging for DevCommand.

Provides JSON-structured logging to file and human-readable stderr
output.  Includes contextual fields (service, tick, duration) and
performance-aware formatters.

Optimised for macOS — uses ``os.getpid()`` once at init to avoid
repeated syscalls.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR = Path.home() / ".devcommand" / "logs"
_PID = os.getpid()


class StructuredFormatter(logging.Formatter):
    """Emit logs as single-line JSON objects.

    Fields: ``ts``, ``level``, ``logger``, ``msg``, ``pid``,
    plus any extras attached via :func:`log_context`.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "pid": _PID,
        }
        # Merge extra context
        for key in ("service", "tick", "duration_ms", "plugin", "panel"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val

        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
            entry["error_type"] = type(record.exc_info[1]).__name__

        return json.dumps(entry, default=str)


class HumanFormatter(logging.Formatter):
    """Compact colourless formatter for stderr."""

    _FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DATE_FMT = "%H:%M:%S"

    def __init__(self) -> None:
        super().__init__(self._FMT, datefmt=self._DATE_FMT)


def configure_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    debug: bool = False,
) -> None:
    """Set up structured application-wide logging.

    Args:
        level: Root log level (overridden to DEBUG if *debug* is True).
        log_to_file: Write JSON logs to ``~/.devcommand/logs/``.
        debug: Enable DEBUG level and verbose console output.
    """
    if debug:
        level = logging.DEBUG

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Console → stderr (human-readable, WARNING+ normally, DEBUG if --debug)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if debug else logging.WARNING)
    console.setFormatter(HumanFormatter())
    root.addHandler(console)

    # File → JSON structured
    if log_to_file:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(
            _LOG_DIR / "devcommand.log", encoding="utf-8"
        )
        fh.setLevel(level)
        fh.setFormatter(StructuredFormatter())
        root.addHandler(fh)

    # Silence noisy third-party
    for name in ("docker", "urllib3", "git", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def log_context(**kwargs: Any) -> dict[str, Any]:
    """Return an ``extra`` dict for structured log fields.

    Usage::

        logger.info("Tick complete", extra=log_context(tick=5, duration_ms=120))
    """
    return kwargs
