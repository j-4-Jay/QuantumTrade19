"""QuantumTrade19 runtime logging: quiet console, complete rotating file logs."""
from __future__ import annotations

import logging
import logging.handlers
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
    """Format all persisted runtime records with UTC timestamps."""

    converter = staticmethod(__import__("time").gmtime)


def _formatter() -> logging.Formatter:
    return _UTCFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure a quiet terminal and complete daily-rotating runtime files."""
    global _CONFIGURED
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        formatter = _formatter()
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

        # The terminal is intentionally reserved for application errors.
        # Reflex still prints its own startup URLs separately.
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.ERROR)
        console.setFormatter(formatter)

        all_events = logging.handlers.TimedRotatingFileHandler(
            _LOG_DIR / "quantumtrade19.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            utc=True,
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
        )
        errors.setLevel(logging.WARNING)
        errors.setFormatter(formatter)

        root.addHandler(console)
        root.addHandler(all_events)
        root.addHandler(errors)

        # These framework/client lifecycle warnings are expected in Reflex
        # development reloads and are retained in quantumtrade19.log only.
        logging.getLogger("reflex").setLevel(logging.ERROR)
        logging.getLogger("reflex.state").setLevel(logging.ERROR)
        logging.getLogger("socketio").setLevel(logging.ERROR)
        logging.getLogger("engineio").setLevel(logging.ERROR)
        logging.captureWarnings(True)
        _install_exception_hooks()
        _CONFIGURED = True
        logging.getLogger("system.logging").info(
            "logging_configured log_dir=%s retention_days=30 console_level=ERROR",
            _LOG_DIR,
        )


def _install_exception_hooks() -> None:
    """Persist unhandled main-thread and worker-thread exceptions."""
    logger = logging.getLogger("system.unhandled_exception")

    def main_hook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "unhandled_main_thread_exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        logger.critical(
            "unhandled_worker_thread_exception thread=%s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
