from unittest.mock import AsyncMock

import pytest

from app.db import complaints as db
from app.services import officer_service as os_
from app.state.conversation_state import ConversationState as S
from tests.conftest import make_complaint_dict


@pytest.fixture
def wa(monkeypatch):
    """Stub every outgoing WhatsApp / storage call."""
    stubs = {
        "text": AsyncMock(return_value={"messages": [{"id": "wamid.T"}]}),
        "template": AsyncMock(return_value={"messages": [{"id": "wamid.TPL"}]}),
        "image": AsyncMock(return_value={}),
        "photo": AsyncMock(return_value="resolved/NLG/m.jpeg"),
    }
    monkeypatch.setattr(os_, "send_text_message", stubs["text"])
    monkeypatch.setattr(os_, "send_template_message", stubs["template"])
    monkeypatch.setattr(os_, "send_image_message", stubs["image"])
    monkeypatch.setattr(os_, "save_whatsapp_photo", stubs["photo"])
    return stubs


async def filed(session, **over):
    row = await db.save_complaint(session, make_complaint_dict(**over))
    await session.commit()
    return row


def text_msg(body, **extra):
    return {"type": "text", "text": {"body": body}, **extra}


def image_msg(caption=None, **extra):
    image = {"id": "m1"}
    if caption:
        image["caption"] = caption
    return {"type": "image", "image": image, **extra}


# ---------- is_officer_reply ----------


async def test_is_reply_by_context(session, officer):
    c = await filed(session)
    c.notification_wamid = "wamid.N"
    await session.commit()
    msg = text_msg("done", context={"id": "wamid.N"})
    assert await os_.is_officer_reply(session, officer, msg, S.START)


async def test_is_reply_by_reference_in_text_and_caption(session, officer):
    assert await os_.is_officer_reply(
        session, officer, text_msg("fixed nlg-2026-00001"), S.START
    )
    assert await os_.is_officer_reply(
        session, officer, image_msg("NLG-2026-00001"), S.START
    )


async def test_is_reply_plain_text_is_not(session, officer):
    assert not await os_.is_officer_reply(
        session, officer, text_msg("hello"), S.START
    )


async def test_is_reply_photo_depends_on_state(session, officer):
    assert await os_.is_officer_reply(session, officer, image_msg(), S.START)
    assert not await os_.is_officer_reply(
        session, officer, image_msg(), S.WAITING_FOR_PHOTO
    )


async def test_is_reply_other_types(session, officer):
    msg = {"type": "location", "location": {}}
    assert not await os_.is_officer_reply(session, officer, msg, S.START)


# ---------- notify_officer ----------


async def test_notify_text_success(session, officer, wa):
    c = await filed(session, custom_complaint="bad smell")
    assert await os_.notify_officer(officer, c) == "wamid.T"
    body = wa["text"].await_args.args[1]
    assert c.reference_no in body and "bad smell" in body
    assert "maps.google.com" in body and "Asha" in body
    wa["template"].assert_not_awaited()


async def test_notify_falls_back_to_template(session, officer, wa):
    wa["text"].side_effect = RuntimeError("outside window")
    c = await filed(session)
    assert await os_.notify_officer(officer, c) == "wamid.TPL"
    params = wa["template"].await_args.args[3]
    assert params[0] == c.reference_no and "maps.google.com" in params[3]


async def test_notify_template_uses_location_text_without_coords(
    session, officer, wa
):
    wa["text"].side_effect = RuntimeError
    c = await filed(session, latitude=None, longitude=None)
    await os_.notify_officer(officer, c)
    assert wa["template"].await_args.args[3][3] == "Main road"


async def test_notify_returns_none_when_all_fail(session, officer, wa):
    wa["text"].side_effect = RuntimeError
    wa["template"].side_effect = RuntimeError
    c = await filed(session)
    assert await os_.notify_officer(officer, c) is None


# ---------- handle_officer_message ----------


async def test_resolve_by_reference_with_photo(session, officer, wa):
    c = await filed(session)
    await os_.handle_officer_message(
        session, officer, image_msg(c.reference_no)
    )
    assert c.officer_status == "resolved"
    assert c.resolved_photo_url == "resolved/NLG/m.jpeg"
    wa["photo"].assert_awaited_once_with("m1", f"resolved/{c.reference_no}")
    wa["image"].assert_awaited_once()
    assert wa["image"].await_args.args[0] == c.phone_number


async def test_resolve_by_reply_context_text_only(session, officer, wa):
    c = await filed(session)
    c.notification_wamid = "wamid.N"
    await session.commit()
    await os_.handle_officer_message(
        session, officer, text_msg("done", context={"id": "wamid.N"})
    )
    assert c.officer_status == "resolved"
    wa["photo"].assert_not_awaited()
    # citizen gets a text notice, not an image
    assert wa["text"].await_args_list[-1].args[0] == c.phone_number


async def test_reference_not_assigned(session, officer, wa):
    await os_.handle_officer_message(
        session, officer, text_msg("NLG-2026-99999")
    )
    assert "not assigned" in wa["text"].await_args.args[1]


async def test_no_pending(session, officer, wa):
    await os_.handle_officer_message(session, officer, text_msg("hi"))
    assert wa["text"].await_args.args[1] == "No pending complaints."


async def test_text_without_reference_lists_pending(session, officer, wa):
    c = await filed(session)
    await os_.handle_officer_message(session, officer, text_msg("hi"))
    msg = wa["text"].await_args.args[1]
    assert c.reference_no in msg and "send a photo" in msg
    assert c.officer_status == "pending"


async def test_photo_single_pending_resolves_it(session, officer, wa):
    c = await filed(session)
    await os_.handle_officer_message(session, officer, image_msg())
    assert c.officer_status == "resolved"


async def test_photo_with_many_pending_asks_for_reference(
    session, officer, wa
):
    a = await filed(session)
    b = await filed(session)
    await os_.handle_officer_message(session, officer, image_msg())
    msg = wa["text"].await_args.args[1]
    assert a.reference_no in msg and b.reference_no in msg
    assert a.officer_status == "pending"


async def test_already_resolved(session, officer, wa):
    c = await filed(session)
    await db.mark_resolved(session, c, None)
    await os_.handle_officer_message(
        session, officer, text_msg(c.reference_no)
    )
    assert "already marked resolved" in wa["text"].await_args.args[1]
    wa["image"].assert_not_awaited()


async def test_storage_failure_falls_back_to_media_id(session, officer, wa):
    wa["photo"].side_effect = RuntimeError("storage down")
    c = await filed(session)
    await os_.handle_officer_message(
        session, officer, image_msg(c.reference_no)
    )
    assert c.resolved_photo_url == "m1"


async def test_citizen_notice_failure_is_swallowed(session, officer, wa):
    wa["image"].side_effect = RuntimeError
    c = await filed(session)
    await os_.handle_officer_message(
        session, officer, image_msg(c.reference_no)
    )
    assert c.officer_status == "resolved"
