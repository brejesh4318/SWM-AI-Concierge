from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import webhook
from app.main import app
from app.services import messages
from app.state import conversation_manager as cm
from app.state.conversation_state import ConversationState as S

U = "919811111111"


def envelope(message, contacts=None):
    value = {"messages": [message]}
    if contacts is not None:
        value["contacts"] = contacts
    return {"entry": [{"changes": [{"value": value}]}]}


def text(body, mid="wamid.in"):
    return {"from": U, "id": mid, "type": "text", "text": {"body": body}}


def list_reply(rid):
    return {
        "from": U,
        "id": "w",
        "type": "interactive",
        "interactive": {"type": "list_reply", "list_reply": {"id": rid}},
    }


def button_reply(rid):
    return {
        "from": U,
        "id": "w",
        "type": "interactive",
        "interactive": {"type": "button_reply", "button_reply": {"id": rid}},
    }


@pytest.fixture
def senders(monkeypatch):
    """Replace every outgoing sender in the webhook with an AsyncMock."""
    names = [
        "send_block_menu",
        "send_complaint_menu",
        "send_language_menu",
        "send_local_body_menu",
        "send_local_body_type_menu",
        "send_photo_question",
        "send_text_message",
    ]
    mocks = {}
    for n in names:
        mocks[n] = AsyncMock()
        monkeypatch.setattr(webhook, n, mocks[n])
    return mocks


# ---------- verification handshake ----------


def test_root_health():
    assert TestClient(app).get("/").json() == {
        "message": "WhatsApp Bot is Running"
    }


def test_verify_webhook_ok_and_rejected():
    client = TestClient(app)
    ok = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": webhook.VERIFY_TOKEN,
            "hub.challenge": "1234",
        },
    )
    assert ok.status_code == 200 and ok.text == "1234"
    bad = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong"},
    )
    assert bad.status_code == 403


def test_sender_of():
    assert webhook._sender_of(envelope(text("x"))) == U
    assert webhook._sender_of({}) is None
    assert webhook._sender_of({"entry": [{"changes": [{"value": {}}]}]}) is None


# ---------- _process routing ----------


async def test_no_messages_returns_received(senders):
    data = {"entry": [{"changes": [{"value": {"statuses": []}}]}]}
    assert await webhook._process(data) == {"status": "received"}


async def test_text_hi_sends_language_menu_and_saves_profile(senders):
    data = envelope(text("hi"), contacts=[{"profile": {"name": "Asha"}}])
    await webhook._process(data)
    senders["send_language_menu"].assert_awaited_once_with(recipient_phone=U)
    assert cm.get_data_value(U, "customer_name") == "Asha"
    assert cm.get_data_value(U, "phone_number") == U


async def test_language_button_sends_complaint_menu(senders):
    cm.set_state(U, S.WAITING_FOR_LANGUAGE)
    await webhook._process(envelope(button_reply("lang_ta")))
    senders["send_complaint_menu"].assert_awaited_once_with(
        recipient_phone=U, language="ta"
    )


async def test_unknown_button_gets_invalid_option(senders):
    await webhook._process(envelope(button_reply("zzz")))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "invalid_option")


async def test_photo_yes_button(senders):
    cm.set_state(U, S.ASKING_FOR_PHOTO)
    await webhook._process(envelope(button_reply("photo_yes")))
    assert cm.get_state(U) == S.WAITING_FOR_PHOTO


async def test_list_reply_complaint_choice(senders):
    cm.set_state(U, S.WAITING_FOR_COMPLAINT)
    await webhook._process(envelope(list_reply("complaint_1")))
    senders["send_local_body_type_menu"].assert_awaited_once()


async def test_list_reply_unknown_id(senders):
    await webhook._process(envelope(list_reply("garbage")))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "invalid_option")


async def test_list_reply_type_and_body_flow(senders):
    cm.set_state(U, S.WAITING_FOR_LOCAL_BODY_TYPE)
    await webhook._process(envelope(list_reply("lbtype_municipality")))
    senders["send_local_body_menu"].assert_awaited_once()
    await webhook._process(envelope(list_reply("lb_0")))
    assert cm.get_state(U) == S.WAITING_FOR_WARD


async def test_unsupported_interactive_type(senders):
    msg = {
        "from": U,
        "id": "w",
        "type": "interactive",
        "interactive": {"type": "nfm_reply"},
    }
    await webhook._process(envelope(msg))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "use_options")


async def test_location_message(senders):
    cm.set_state(U, S.WAITING_FOR_LOCATION)
    msg = {
        "from": U,
        "id": "w",
        "type": "location",
        "location": {"latitude": 11.3, "longitude": 76.7},
    }
    await webhook._process(envelope(msg))
    senders["send_photo_question"].assert_awaited_once()
    assert cm.get_data_value(U, "latitude") == 11.3


async def test_unreadable_location(senders):
    msg = {"from": U, "id": "w", "type": "location", "location": {}}
    await webhook._process(envelope(msg))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "location_unreadable")


async def test_image_saved_and_completes(senders, monkeypatch):
    monkeypatch.setattr(
        webhook, "save_whatsapp_photo", AsyncMock(return_value="U/m.jpeg")
    )
    session = MagicMock(commit=AsyncMock())
    monkeypatch.setattr(
        webhook, "already_saved", AsyncMock(return_value=None)
    )
    saved = MagicMock(reference_no="NLG-2026-00001", notification_wamid=None)
    monkeypatch.setattr(
        webhook, "save_complaint", AsyncMock(return_value=saved)
    )
    monkeypatch.setattr(
        webhook, "officer_for", AsyncMock(return_value=MagicMock())
    )
    notify = AsyncMock(return_value="wamid.N")
    monkeypatch.setattr(webhook, "notify_officer", notify)

    cm.set_state(U, S.WAITING_FOR_PHOTO)
    msg = {"from": U, "id": "w", "type": "image", "image": {"id": "m"}}
    await webhook._process(envelope(msg), session)

    assert cm.get_data_value(U, "photo_media_id") == "U/m.jpeg"
    notify.assert_awaited_once()
    assert saved.notification_wamid == "wamid.N"
    assert session.commit.await_count == 2
    receipt = senders["send_text_message"].await_args.kwargs["message"]
    assert "NLG-2026-00001" in receipt


async def test_image_storage_failure_keeps_media_id(senders, monkeypatch):
    monkeypatch.setattr(
        webhook, "save_whatsapp_photo", AsyncMock(side_effect=RuntimeError)
    )
    cm.set_state(U, S.WAITING_FOR_PHOTO)
    msg = {"from": U, "id": "w", "type": "image", "image": {"id": "raw"}}
    # session=None would crash on completion; the error path must still reply.
    await webhook._process(envelope(msg))
    assert cm.get_data_value(U, "photo_media_id") == "raw"


async def test_image_without_id(senders):
    msg = {"from": U, "id": "w", "type": "image", "image": {}}
    await webhook._process(envelope(msg))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "photo_unreadable")


async def test_unsupported_type(senders):
    msg = {"from": U, "id": "w", "type": "sticker"}
    await webhook._process(envelope(msg))
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "unsupported")


async def test_duplicate_delivery_does_not_resave(senders, monkeypatch):
    existing = MagicMock(reference_no="NLG-2026-00007")
    monkeypatch.setattr(
        webhook, "already_saved", AsyncMock(return_value=existing)
    )
    save = AsyncMock()
    monkeypatch.setattr(webhook, "save_complaint", save)
    monkeypatch.setattr(
        webhook, "officer_for", AsyncMock(return_value=None)
    )
    notify = AsyncMock()
    monkeypatch.setattr(webhook, "notify_officer", notify)

    cm.set_state(U, S.ASKING_FOR_PHOTO)
    session = MagicMock(commit=AsyncMock())
    await webhook._process(envelope(text("no")), session)

    save.assert_not_awaited()
    notify.assert_not_awaited()
    receipt = senders["send_text_message"].await_args.kwargs["message"]
    assert "NLG-2026-00007" in receipt
    assert messages.t("en", "receipt_no_officer") in receipt


async def test_processing_error_rolls_back_and_notifies(senders):
    senders["send_language_menu"].side_effect = RuntimeError("boom")
    session = MagicMock(rollback=AsyncMock())
    result = await webhook._process(envelope(text("hi")), session)
    assert result == {"status": "received"}
    session.rollback.assert_awaited_once()
    sent = senders["send_text_message"].await_args.kwargs["message"]
    assert sent == messages.t("en", "error_try_again")


async def test_error_notice_failure_is_swallowed(senders):
    senders["send_language_menu"].side_effect = RuntimeError
    senders["send_text_message"].side_effect = RuntimeError
    assert await webhook._process(envelope(text("hi"))) == {
        "status": "received"
    }


# ---------- POST /webhook ----------


@pytest.fixture
def post_env(monkeypatch):
    session = MagicMock(rollback=AsyncMock())

    @asynccontextmanager
    async def fake_session_local():
        yield session

    monkeypatch.setattr(webhook, "SessionLocal", fake_session_local)
    monkeypatch.setattr(webhook, "load_user", AsyncMock())
    persist = AsyncMock()
    monkeypatch.setattr(webhook, "persist_user", persist)
    process = AsyncMock(return_value={"status": "received"})
    monkeypatch.setattr(webhook, "_process", process)
    return {"persist": persist, "process": process, "session": session}


def test_post_status_update_is_ignored(post_env):
    body = {"entry": [{"changes": [{"value": {"statuses": [{}]}}]}]}
    r = TestClient(app).post("/webhook", json=body)
    assert r.json() == {"status": "received"}
    post_env["persist"].assert_not_awaited()


def test_post_citizen_goes_to_process_and_persists(post_env, monkeypatch):
    monkeypatch.setattr(
        webhook, "officer_by_phone", AsyncMock(return_value=None)
    )
    r = TestClient(app).post("/webhook", json=envelope(text("hi")))
    assert r.json() == {"status": "received"}
    post_env["process"].assert_awaited_once()
    post_env["persist"].assert_awaited_once()


def test_post_officer_reply_bypasses_chatbot(post_env, monkeypatch):
    monkeypatch.setattr(
        webhook, "officer_by_phone", AsyncMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        webhook, "is_officer_reply", AsyncMock(return_value=True)
    )
    handler = AsyncMock()
    monkeypatch.setattr(webhook, "handle_officer_message", handler)
    TestClient(app).post("/webhook", json=envelope(text("NLG-2026-00001")))
    handler.assert_awaited_once()
    post_env["process"].assert_not_awaited()
    post_env["persist"].assert_awaited_once()


def test_post_officer_handler_error_rolls_back(post_env, monkeypatch):
    monkeypatch.setattr(
        webhook, "officer_by_phone", AsyncMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        webhook, "is_officer_reply", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        webhook,
        "handle_officer_message",
        AsyncMock(side_effect=RuntimeError),
    )
    r = TestClient(app).post("/webhook", json=envelope(text("x")))
    assert r.json() == {"status": "received"}
    post_env["session"].rollback.assert_awaited_once()
    post_env["persist"].assert_awaited_once()


def test_post_officer_non_reply_is_treated_as_citizen(post_env, monkeypatch):
    monkeypatch.setattr(
        webhook, "officer_by_phone", AsyncMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        webhook, "is_officer_reply", AsyncMock(return_value=False)
    )
    TestClient(app).post("/webhook", json=envelope(text("hi")))
    post_env["process"].assert_awaited_once()
