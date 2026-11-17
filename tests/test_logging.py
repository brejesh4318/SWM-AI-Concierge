import json
import logging

from app.core.logging import (
    _ContextFilter,
    _JsonFormatter,
    bind_user,
    mask_phone,
    request_id_var,
)


def test_mask_phone_keeps_last_four_digits():
    assert mask_phone("918098059300") == "********9300"


def test_mask_phone_handles_missing_and_short_numbers():
    assert mask_phone(None) == "-"
    assert mask_phone("") == "-"
    assert mask_phone("123") == "123"


def test_json_formatter_includes_context_and_masked_user():
    request_id_var.set("abc123")
    bind_user("918098059300")

    record = logging.LogRecord(
        "app.test", logging.INFO, __file__, 1, "hello %s", ("world",), None
    )
    _ContextFilter().filter(record)

    entry = json.loads(_JsonFormatter().format(record))

    assert entry["message"] == "hello world"
    assert entry["request_id"] == "abc123"
    assert entry["user"] == "********9300"
    assert "918098059300" not in json.dumps(entry)
