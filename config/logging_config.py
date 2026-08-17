"""
FULL PATH: config/logging_config.py (NEW FILE)

QuantumTrade19 runtime logging foundation.

Call configure_logging() exactly once, at application process startup, before
any Worker/background thread is created. The configuration is idempotent, so
an accidental second call is harmless and does not duplicate handlers.

Files written under logs/ (never source tree):
  quantumtrade19.log       all application events, rotates at midnight UTC
  errors.log               WARNING and above only, rotates at midnight UTC

Retention: 30 rotated files per stream. Uses Python standard library only.
Never log API keys, auth tokens, cookies, raw signed requests, or full HTTP
headers. Worker logs must use symbol/TF/status/error-class context only.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False

LOG_FORMAT = "%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class _UTCFormatter(logging.Formatter):
    """Forces all log timestamps to UTC so event correlation is unambiguous."""

    converter = staticmethod(__import__("time").gmtime)


class _MaxLevelFilter(logging.Filter):
    """Allows records only up to (and including) max_level."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def _make_formatter() -> logging.Formatter:
    return _UTCFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure console + daily rotating application/error log files once."""
    global _CONFIGURED
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        formatter = _make_formatter()
        root = logging.getLogger()
        root.setLevel(level)

        # Avoid duplicate output under Reflex/Uvicorn reload behavior.
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(formatter)

        all_events = logging.handlers.TimedRotatingFileHandler(
            _LOG_DIR / "quantumtrade19.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            utc=True,
            delay=False,
        )
        all_events.setLevel(level)
        all_events.setFormatter(formatter)

        errors = logging.handlers.TimedRotatingFileHandler(
            _LOG_DIR / "errors.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            utc=True,
            delay=False,
        )
        errors.setLevel(logging.WARNING)
        errors.setFormatter(formatter)

        root.addHandler(console)
        root.addHandler(all_events)
        root.addHandler(errors)

        logging.captureWarnings(True)
        _install_exception_hooks()
        _CONFIGURED = True
        logging.getLogger("system.logging").info(
            "logging_configured log_dir=%s retention_days=30", _LOG_DIR
        )


def _install_exception_hooks() -> None:
    """Persist crashes from main thread and otherwise-silent worker threads."""
    logger = logging.getLogger("system.unhandled_exception")

    def _main_exception_hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("unhandled_main_thread_exception", exc_info=(exc_type, exc_value, exc_traceback))

    def _thread_exception_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        logger.critical(
            "unhandled_worker_thread_exception thread=%s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _main_exception_hook
    threading.excepthook = _thread_exception_hook
