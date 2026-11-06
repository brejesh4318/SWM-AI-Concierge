# -*- coding: utf-8 -*-
"""Logging setup: one format, request ids, and masked phone numbers."""

import json
import logging
import sys
from contextvars import ContextVar
import time
from contextlib import contextmanager


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_var: ContextVar[str] = ContextVar("user", default="-")


def mask_phone(phone: str | None) -> str:
    """Hide all but the last four digits of a phone number.

    Args:
        phone: A phone number, or None.

    Returns:
        For example '********9300', or '-' if there is no number.
    """

    if not phone:
        return "-"

    phone = str(phone)

    return "*" * max(len(phone) - 4, 0) + phone[-4:]


def bind_user(phone: str | None) -> None:
    """Tag every log line of the current request with this user.

    Args:
        phone: The user's phone number. It is masked before use.
    """

    user_var.set(mask_phone(phone))


class _ContextFilter(logging.Filter):
    """Copy the request id and user onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user = user_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    """Render each record as one JSON object, for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": record.request_id,
            "user": record.user,
            "message": record.getMessage(),
        }

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure the root logger once for the whole application.

    Safe to call more than once; earlier handlers are replaced.

    Args:
        level: A logging level name such as 'DEBUG' or 'INFO'.
        json_output: Emit one JSON object per line instead of text.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    handler.setFormatter(
        _JsonFormatter()
        if json_output
        else logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s "
            "[%(request_id)s %(user)s] %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # httpx logs full URLs at INFO and SQLAlchemy echoes every query;
    # keep both quiet unless the app is explicitly in DEBUG.
    noisy = logging.DEBUG if level.upper() == "DEBUG" else logging.WARNING
    logging.getLogger("httpx").setLevel(noisy)
    logging.getLogger("httpcore").setLevel(noisy)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

@contextmanager
def timed(label: str):
    """Log how long the wrapped block takes, in milliseconds."""

    started = time.perf_counter()
    try:
        yield
    finally:
        logging.getLogger("timing").info(
            "%s took %.0f ms", label, (time.perf_counter() - started) * 1000
        )
