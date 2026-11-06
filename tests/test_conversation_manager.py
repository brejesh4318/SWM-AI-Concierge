from unittest.mock import AsyncMock, MagicMock

from app.db.models import ConversationStateRow
from app.state import conversation_manager as cm
from app.state.conversation_state import ConversationState as S

U = "9190"


def test_state_defaults_to_start_and_sets():
    assert cm.get_state(U) == S.START
    cm.set_state(U, S.WAITING_FOR_WARD)
    assert cm.get_state(U) == S.WAITING_FOR_WARD


def test_data_roundtrip_and_default():
    cm.save_data(U, "a", 1)
    assert cm.get_data_value(U, "a") == 1
    assert cm.get_data_value(U, "b", "d") == "d"
    cm.get_data(U)["x"] = 2
    assert cm.get_data_value(U, "x") == 2


def test_language():
    assert cm.get_language(U) == ""
    cm.set_language(U, "ta")
    assert cm.get_language(U) == "ta"


def test_reset_keeps_language_forget_clears_it():
    cm.set_state(U, S.COMPLETED)
    cm.save_data(U, "k", "v")
    cm.set_language(U, "ta")
    cm.reset_conversation(U)
    assert cm.get_state(U) == S.START
    assert cm.get_data(U) == {}
    assert cm.get_language(U) == "ta"
    cm.forget_user(U)
    assert cm.get_language(U) == ""


async def test_load_user_missing_row_noop():
    session = MagicMock(get=AsyncMock(return_value=None))
    await cm.load_user(U, session)
    assert cm.get_state(U) == S.START


async def test_load_user_populates_memory():
    row = ConversationStateRow(
        phone_number=U, state="WAITING_FOR_WARD", language="ta", data={"a": 1}
    )
    session = MagicMock(get=AsyncMock(return_value=row))
    await cm.load_user(U, session)
    assert cm.get_state(U) == S.WAITING_FOR_WARD
    assert cm.get_data(U) == {"a": 1}
    assert cm.get_language(U) == "ta"


async def test_persist_creates_row_and_clears_memory():
    session = MagicMock(
        get=AsyncMock(return_value=None), commit=AsyncMock(), add=MagicMock()
    )
    cm.set_state(U, S.WAITING_FOR_LOCATION)
    cm.set_language(U, "en")
    cm.save_data(U, "k", "v")
    await cm.persist_user(U, session)
    added = session.add.call_args.args[0]
    assert added.state == "WAITING_FOR_LOCATION"
    assert added.language == "en" and added.data == {"k": "v"}
    session.commit.assert_awaited_once()
    assert cm.get_state(U) == S.START and cm.get_language(U) == ""


async def test_persist_updates_existing_row():
    row = ConversationStateRow(phone_number=U, state="START", data={})
    session = MagicMock(
        get=AsyncMock(return_value=row), commit=AsyncMock(), add=MagicMock()
    )
    cm.set_state(U, S.COMPLETED)
    await cm.persist_user(U, session)
    assert row.state == "COMPLETED" and row.language is None
    session.add.assert_not_called()


async def test_persist_deletes_when_forgotten():
    row = ConversationStateRow(phone_number=U, state="START", data={})
    session = MagicMock(
        get=AsyncMock(return_value=row),
        commit=AsyncMock(),
        delete=AsyncMock(),
    )
    await cm.persist_user(U, session)
    session.delete.assert_awaited_once_with(row)
