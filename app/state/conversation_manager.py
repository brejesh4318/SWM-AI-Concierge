from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationStateRow

from app.state.conversation_state import ConversationState


conversation_states: dict[str, ConversationState] = {}

conversation_data: dict[str, dict[str, Any]] = {}

# Kept apart from conversation_data so a mid-flow
# reset_conversation() does not lose it.  Starting a brand new
# complaint goes through forget_user(), which does clear it so
# the language prompt is shown again.
conversation_language: dict[str, str] = {}


def get_state(user_id: str) -> ConversationState:
    """Look up where a user is in the conversation flow.

    Args:
        user_id: The user's phone number.

    Returns:
        The user's current ConversationState, or ConversationState.START
        if nothing is stored for them.
    """
    return conversation_states.get(
        user_id,
        ConversationState.START,
    )


def set_state(
    user_id: str,
    state: ConversationState,
) -> None:
    """Record the user's current conversation state in memory.

    Args:
        user_id: The user's phone number.
        state: The state to store.
    """
    conversation_states[user_id] = state


def get_data(user_id: str) -> dict[str, Any]:
    """Fetch the answers collected from a user so far.

    Args:
        user_id: The user's phone number.

    Returns:
        The user's data dictionary. An empty one is created and stored
        if none exists yet, so changes to it persist.
    """
    return conversation_data.setdefault(
        user_id,
        {},
    )


def save_data(
    user_id: str,
    key: str,
    value: Any,
) -> None:
    """Store a single answer for a user.

    Args:
        user_id: The user's phone number.
        key: The name of the field to store.
        value: The value to store under that key.
    """
    data = get_data(user_id)
    data[key] = value


def get_data_value(
    user_id: str,
    key: str,
    default: Any = None,
) -> Any:
    """Read a single answer for a user.

    Args:
        user_id: The user's phone number.
        key: The name of the field to read.
        default: The value to return if the key is not set. Defaults to
            None.

    Returns:
        The stored value, or default if the key is missing.
    """
    return get_data(user_id).get(key, default)


def get_language(user_id: str) -> str:
    """Look up the language a user has chosen.

    Args:
        user_id: The user's phone number.

    Returns:
        The language code, or an empty string if none has been chosen.
    """
    return conversation_language.get(user_id, "")


def set_language(
    user_id: str,
    language: str,
) -> None:
    """Record the language a user has chosen.

    Args:
        user_id: The user's phone number.
        language: The language code to store.
    """
    conversation_language[user_id] = language


def reset_conversation(user_id: str) -> None:
    """Clear a user's state and answers but keep their language.

    Args:
        user_id: The user's phone number.
    """
    conversation_states.pop(user_id, None)
    conversation_data.pop(user_id, None)


def forget_user(user_id: str) -> None:
    """Clear everything stored for a user, including their language.

    The language prompt will be shown again on their next message.

    Args:
        user_id: The user's phone number.
    """
    reset_conversation(user_id)
    conversation_language.pop(user_id, None)

async def load_user(
    user_id: str,
    session: AsyncSession,
) -> None:
    """Pull this user's conversation from the database into memory.

    Does nothing if the user has no saved conversation.

    Args:
        user_id: The user's phone number.
        session: The database session to read from.
    """

    row = await session.get(ConversationStateRow, user_id)

    if row is None:
        return

    conversation_states[user_id] = ConversationState(row.state)
    conversation_data[user_id] = dict(row.data or {})

    if row.language:
        conversation_language[user_id] = row.language


async def persist_user(
    user_id: str,
    session: AsyncSession,
) -> None:
    """Write the conversation back, then drop it from memory.

    Creates, updates or deletes the user's database row depending on
    what is held in memory, and commits the change.

    Args:
        user_id: The user's phone number.
        session: The database session to write to.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the commit fails.
    """

    state = conversation_states.get(user_id)
    language = conversation_language.get(user_id, "")
    data = conversation_data.get(user_id, {})

    row = await session.get(ConversationStateRow, user_id)

    if state is None and not language:

        # forget_user() was called, so remove the row entirely.
        if row is not None:
            await session.delete(row)

    elif row is None:

        session.add(
            ConversationStateRow(
                phone_number=user_id,
                state=(state or ConversationState.START).value,
                language=language or None,
                data=data,
            )
        )

    else:

        row.state = (state or ConversationState.START).value
        row.language = language or None
        row.data = data

    await session.commit()

    conversation_states.pop(user_id, None)
    conversation_data.pop(user_id, None)
    conversation_language.pop(user_id, None)
