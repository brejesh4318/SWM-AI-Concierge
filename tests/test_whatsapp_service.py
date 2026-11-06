from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import messages
from app.services import whatsapp_service as ws

TO = "919800000000"


@pytest.fixture
def sent(monkeypatch):
    """Capture payloads instead of calling the WhatsApp API."""
    mock = AsyncMock(return_value={"messages": [{"id": "wamid.1"}]})
    monkeypatch.setattr(ws, "_send_whatsapp_payload", mock)
    return mock


def payload_of(mock):
    return mock.await_args.args[0]


def test_envelope_and_reply_buttons():
    env = ws._envelope(TO)
    assert env["to"] == TO and env["messaging_product"] == "whatsapp"
    out = ws._reply_buttons([{"id": "a", "title": "A"}])
    assert out == [{"type": "reply", "reply": {"id": "a", "title": "A"}}]


def test_message_id_of():
    assert ws.message_id_of({"messages": [{"id": "x"}]}) == "x"
    assert ws.message_id_of({}) is None
    assert ws.message_id_of({"messages": []}) is None
    assert ws.message_id_of(None) is None


async def test_send_text(sent):
    await ws.send_text_message(TO, "hello")
    p = payload_of(sent)
    assert p["type"] == "text" and p["text"]["body"] == "hello"


async def test_send_template_flattens_params(sent):
    await ws.send_template_message(TO, "tpl", "en", ["a\nb  c", "", 5])
    params = payload_of(sent)["template"]["components"][0]["parameters"]
    assert [x["text"] for x in params] == ["a b c", "-", "5"]


async def test_send_image(sent):
    await ws.send_image_message(TO, "m1", caption="cap")
    assert payload_of(sent)["image"] == {"id": "m1", "caption": "cap"}
    await ws.send_image_message(TO, "m1")
    assert payload_of(sent)["image"] == {"id": "m1"}


async def test_language_menu_buttons(sent):
    await ws.send_language_menu(TO)
    assert payload_of(sent)["type"] == "interactive"


async def test_complaint_menu_is_list(sent):
    await ws.send_complaint_menu(TO, "en")
    inter = payload_of(sent)["interactive"]
    assert inter["type"] == "list"
    rows = inter["action"]["sections"][0]["rows"]
    assert len(rows) == len(messages.menu("en")["rows"])


async def test_photo_question(sent):
    await ws.send_photo_question(TO, "en")
    assert payload_of(sent)["type"] == "interactive"


async def test_local_body_menus(sent):
    await ws.send_local_body_type_menu(TO, "en")
    assert payload_of(sent)["interactive"]["type"] == "list"
    await ws.send_block_menu(TO, "en", "village")
    assert payload_of(sent)["interactive"]["type"] == "list"
    await ws.send_local_body_menu(TO, "en", "municipality", "", 0)
    rows = payload_of(sent)["interactive"]["action"]["sections"][0]["rows"]
    assert 0 < len(rows) <= 10


async def test_send_payload_posts_and_raises(monkeypatch):
    monkeypatch.setattr(ws, "DRY_RUN", False)
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda **kw: real(transport=transport, **kw),
    )
    assert await ws._send_whatsapp_payload({"a": 1}) == {"ok": True}
    assert calls[0].headers["authorization"].startswith("Bearer ")

    monkeypatch.setattr(
        ws, "WHATSAPP_API_URL", "https://graph.facebook.com/bad"
    )
    with pytest.raises(httpx.HTTPStatusError):
        await ws._send_whatsapp_payload({"a": 1})


async def test_dry_run_logs_instead_of_sending(monkeypatch, caplog):
    def handler(request: httpx.Request):
        raise AssertionError("dry run must not call the API")

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        ws.httpx,
        "AsyncClient",
        lambda **kw: real(transport=transport, **kw),
    )
    monkeypatch.setattr(ws, "DRY_RUN", True)
    with caplog.at_level("INFO"):
        result = await ws._send_whatsapp_payload(
            {"type": "text", "to": TO}
        )
    assert result["messages"][0]["id"].startswith("wamid.DRYRUN")
    assert "DRY RUN" in caplog.text
