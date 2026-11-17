# -*- coding: utf-8 -*-
import re

from app.services import local_bodies, messages

from app.state.conversation_manager import (
    get_data,
    get_data_value,
    get_language,
    forget_user,
    get_state,
    save_data,
    set_language,
    set_state,
)

from app.state.conversation_state import ConversationState


RESTART_KEYWORDS = {
    "hi",
    "hello",
    "start",
    "new complaint",
    "வணக்கம்",
    "புதிய புகார்",
}


def language_of(user_id: str) -> str:
    """Language for replies; falls back to English until chosen.

    Args:
        user_id: The user's phone number.

    Returns:
        The normalized language code to reply in.
    """
    return messages.normalize(get_language(user_id))


def _text(user_id: str, key: str) -> dict:
    """Build a plain-text reply in the user's language.

    Args:
        user_id: The user's phone number.
        key: The message key to look up in the messages module.

    Returns:
        A result dictionary with 'type' set to 'text' and the translated
        text under 'message'.
    """
    return {
        "type": "text",
        "message": messages.t(language_of(user_id), key),
    }


def _ask_language(user_id: str) -> dict:
    """Move the user to the language step and request the language menu.

    Args:
        user_id: The user's phone number.

    Returns:
        A result dictionary with 'type' set to 'language_menu'.
    """
    set_state(
        user_id,
        ConversationState.WAITING_FOR_LANGUAGE,
    )

    return {
        "type": "language_menu",
    }


WARD_PATTERN = re.compile(r"\d{1,4}")


def _match_local_body_type(
    language: str,
    message: str,
):
    """Map typed input onto a local body type, in either language.

    Accepts the menu number (1 to 3), the internal type key, or the
    translated label in any supported language, ignoring case.

    Args:
        language: The user's language code.
        message: The text the user typed.

    Returns:
        The matching local body type key, or None if nothing matches.
    """

    typed = message.strip().lower()

    numbers = {
        "1": local_bodies.MUNICIPALITY,
        "2": local_bodies.TOWN,
        "3": local_bodies.VILLAGE,
    }

    if typed in numbers:
        return numbers[typed]

    if typed in local_bodies.TYPE_ORDER:
        return typed

    for lang in messages.SUPPORTED_LANGUAGES:
        labels = messages.LOCAL_BODY[lang]["type"]["labels"]

        for key, label in labels.items():
            if typed == label.lower():
                return key

    return None


def _ask_local_body_type(user_id: str) -> dict:
    """Move the user to the local body type step and request its menu.

    Args:
        user_id: The user's phone number.

    Returns:
        A result dictionary with 'type' set to 'local_body_type_menu'.
    """
    set_state(
        user_id,
        ConversationState.WAITING_FOR_LOCAL_BODY_TYPE,
    )

    return {
        "type": "local_body_type_menu",
    }


def _ask_local_body(user_id: str) -> dict:
    """Show the first page of local bodies for the stored type.

    Args:
        user_id: The user's phone number.

    Returns:
        A result dictionary with 'type' set to 'local_body_menu'.
    """

    save_data(user_id, "local_body_offset", 0)

    set_state(
        user_id,
        ConversationState.WAITING_FOR_LOCAL_BODY,
    )

    return {
        "type": "local_body_menu",
    }


def local_body_context(user_id: str) -> dict:
    """What the sender needs to build the current local body page.

    Args:
        user_id: The user's phone number.

    Returns:
        A dictionary with the 'body_type', 'block' and 'offset' stored
        for the user, using '', '' and 0 when they are not set.
    """

    return {
        "body_type": get_data_value(
            user_id,
            "local_body_type",
            "",
        ),
        "block": get_data_value(
            user_id,
            "local_body_block",
            "",
        ),
        "offset": get_data_value(
            user_id,
            "local_body_offset",
            0,
        ),
    }


def select_local_body_type(
    user_id: str,
    body_type: str,
) -> dict:
    """Store the chosen local body type and ask for the next detail.

    Args:
        user_id: The user's phone number.
        body_type: The chosen local body type key.

    Returns:
        A result dictionary with 'type' set to 'block_menu' if the type
        must be narrowed by block first, otherwise 'local_body_menu'.
    """

    save_data(user_id, "local_body_type", body_type)
    save_data(user_id, "local_body_block", "")

    # Village panchayats do not fit one WhatsApp list, so they are
    # narrowed by block first.
    if local_bodies.needs_block(body_type):

        set_state(
            user_id,
            ConversationState.WAITING_FOR_BLOCK,
        )

        return {
            "type": "block_menu",
        }

    return _ask_local_body(user_id)


def select_block(
    user_id: str,
    block: str,
) -> dict:
    """Store the chosen block and show the local bodies within it.

    Args:
        user_id: The user's phone number.
        block: The chosen block name.

    Returns:
        A result dictionary with 'type' set to 'local_body_menu'.
    """

    save_data(user_id, "local_body_block", block)

    return _ask_local_body(user_id)


def select_local_body(
    user_id: str,
    index: int,
) -> dict:
    """Store the chosen local body and ask for the ward number.

    Args:
        user_id: The user's phone number.
        index: The position of the chosen local body in the
            local_bodies list.

    Returns:
        A result dictionary with 'type' set to 'text' holding the ward
        prompt.
    """

    body = local_bodies.get(index)

    save_data(user_id, "local_body", body["name"])
    save_data(user_id, "local_body_type", body["type"])
    save_data(user_id, "local_body_block", body["block"])

    set_state(
        user_id,
        ConversationState.WAITING_FOR_WARD,
    )

    return _text(user_id, "ask_ward")


def show_more_local_bodies(user_id: str) -> dict:
    """Advance to the next page of the current local body list.

    Args:
        user_id: The user's phone number.

    Returns:
        A result dictionary with 'type' set to 'local_body_menu'. If the
        user is already on the last page, that page is shown again.
    """

    context = local_body_context(user_id)

    _, next_offset = local_bodies.page(
        context["body_type"],
        context["block"],
        context["offset"],
    )

    if next_offset is None:
        # Already on the last page; just redraw it.
        return {
            "type": "local_body_menu",
        }

    save_data(user_id, "local_body_offset", next_offset)

    return {
        "type": "local_body_menu",
    }


def apply_language(
    user_id: str,
    language: str,
) -> dict:
    """Record the chosen language and move on to the complaint menu.

    Args:
        user_id: The user's phone number.
        language: The chosen language code, normalized before storing.

    Returns:
        A result dictionary with 'type' set to 'complaint_menu'.
    """

    set_language(
        user_id,
        messages.normalize(language),
    )

    set_state(
        user_id,
        ConversationState.WAITING_FOR_COMPLAINT,
    )

    return {
        "type": "complaint_menu",
    }


def process_text_message(
    user_id: str,
    message: str,
) -> dict:
    """Advance the complaint conversation using a text message.

    What the text means depends on the user's current state. It is
    treated as a language choice, complaint number, free-text
    complaint, local body, ward, location, photo answer or restart
    keyword, and the state is moved forward when the input is valid.

    Args:
        user_id: The user's phone number.
        message: The text the user sent. Surrounding whitespace is
            ignored.

    Returns:
        A result dictionary whose 'type' tells the webhook what to
        send next (for example 'text', 'complaint_menu' or
        'completed'). Invalid input returns the current step's prompt
        again.
    """

    message = message.strip()

    state = get_state(user_id)

    # ----------------------------------------
    # START
    # ----------------------------------------

    if state == ConversationState.START:

        return _ask_language(user_id)

    # ----------------------------------------
    # WAITING FOR LANGUAGE
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_LANGUAGE:

        choice = messages.LANGUAGE_KEYWORDS.get(
            message.lower()
        )

        if choice:
            return apply_language(user_id, choice)

        # Anything else: show the prompt again.
        return {
            "type": "language_menu",
        }

    # ----------------------------------------
    # WAITING FOR COMPLAINT
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_COMPLAINT:

        # Custom complaint
        if message == "6":

            set_state(
                user_id,
                ConversationState.WAITING_FOR_CUSTOM_COMPLAINT,
            )

            save_data(
                user_id,
                "complaint_type",
                messages.COMPLAINT_RECORD["6"],
            )

            return _text(user_id, "ask_custom_complaint")

        # Predefined complaint
        if message in messages.COMPLAINT_RECORD:

            save_data(
                user_id,
                "complaint_type",
                messages.COMPLAINT_RECORD[message],
            )

            # Keep the menu choice so the citizen's receipt can be
            # written in their language, while complaint_type stays
            # canonical English for the Collector's record.
            save_data(
                user_id,
                "complaint_choice",
                message,
            )

            return _ask_local_body_type(user_id)

        return {
            "type": "complaint_menu",
        }

    # ----------------------------------------
    # CUSTOM COMPLAINT
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_CUSTOM_COMPLAINT:

        if not message:
            return _text(user_id, "ask_custom_complaint")

        save_data(
            user_id,
            "custom_complaint",
            message,
        )

        return _ask_local_body_type(user_id)

    # ----------------------------------------
    # LOCAL BODY TYPE
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_LOCAL_BODY_TYPE:

        typed = _match_local_body_type(
            language_of(user_id),
            message,
        )

        if typed:
            return select_local_body_type(user_id, typed)

        return {
            "type": "local_body_type_menu",
        }

    # ----------------------------------------
    # BLOCK
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_BLOCK:

        body_type = get_data_value(
            user_id,
            "local_body_type",
            "",
        )

        for block in local_bodies.blocks(body_type):
            if message.lower() == block.lower():
                return select_block(user_id, block)

        return {
            "type": "block_menu",
        }

    # ----------------------------------------
    # LOCAL BODY
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_LOCAL_BODY:

        context = local_body_context(user_id)

        for index in local_bodies.indexes(
            context["body_type"],
            context["block"],
        ):
            if message.lower() == (
                local_bodies.get(index)["name"].lower()
            ):
                return select_local_body(user_id, index)

        return {
            "type": "local_body_menu",
        }

    # ----------------------------------------
    # WARD
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_WARD:

        found = WARD_PATTERN.search(message)

        if not found:
            return _text(user_id, "invalid_ward")

        save_data(
            user_id,
            "ward_number",
            found.group(),
        )

        set_state(
            user_id,
            ConversationState.WAITING_FOR_LOCATION,
        )

        return _text(user_id, "ask_location")

    # ----------------------------------------
    # LOCATION
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_LOCATION:

        if not message:
            return _text(user_id, "ask_location")

        save_data(
            user_id,
            "location_text",
            message,
        )

        set_state(
            user_id,
            ConversationState.ASKING_FOR_PHOTO,
        )

        return {
            "type": "photo_question",
        }

    # ----------------------------------------
    # PHOTO QUESTION
    # ----------------------------------------

    if state == ConversationState.ASKING_FOR_PHOTO:

        normalized = message.lower()

        if normalized in {
            "yes",
            "y",
            "1",
            "ஆம்",
        }:

            set_state(
                user_id,
                ConversationState.WAITING_FOR_PHOTO,
            )

            return _text(user_id, "ask_photo_upload")

        if normalized in {
            "no",
            "n",
            "2",
            "இல்லை",
        }:

            set_state(
                user_id,
                ConversationState.COMPLETED,
            )

            return {
                "type": "completed",
            }

        return {
            "type": "photo_question",
        }

    # ----------------------------------------
    # WAITING FOR PHOTO
    # ----------------------------------------

    if state == ConversationState.WAITING_FOR_PHOTO:

        return _text(user_id, "ask_photo_upload")

    # ----------------------------------------
    # COMPLETED
    # ----------------------------------------

    if state == ConversationState.COMPLETED:

        if message.lower() in RESTART_KEYWORDS:

            # Start over from the very top: the language choice is
            # cleared too, so the user picks it again for the new
            # complaint.
            forget_user(user_id)

            return _ask_language(user_id)

        return _text(user_id, "already_submitted")

    return _text(user_id, "fallback")


def process_location_message(
    user_id: str,
    latitude: str,
    longitude: str,
) -> dict:
    """Handle a shared location pin.

    Args:
        user_id: The user's phone number.
        latitude: The latitude of the shared location.
        longitude: The longitude of the shared location.

    Returns:
        A result dictionary with 'type' set to 'photo_question' if a
        location was expected and has been stored. Otherwise a 'text'
        result asking the user to send hi to start.
    """

    state = get_state(user_id)

    if state != ConversationState.WAITING_FOR_LOCATION:

        return _text(user_id, "send_hi_to_start")

    save_data(
        user_id,
        "latitude",
        latitude,
    )

    save_data(
        user_id,
        "longitude",
        longitude,
    )

    set_state(
        user_id,
        ConversationState.ASKING_FOR_PHOTO,
    )

    return {
        "type": "photo_question",
    }


def process_photo_message(
    user_id: str,
    media_id: str,
) -> dict:
    """Handle an uploaded photo.

    Args:
        user_id: The user's phone number.
        media_id: The WhatsApp media ID of the uploaded image.

    Returns:
        A result dictionary with 'type' set to 'completed' if a photo
        was expected and has been stored. Otherwise a 'text' result
        saying no photo is being asked for.
    """

    state = get_state(user_id)

    if state != ConversationState.WAITING_FOR_PHOTO:

        return _text(user_id, "not_asking_photo")

    save_data(
        user_id,
        "photo_media_id",
        media_id,
    )

    set_state(
        user_id,
        ConversationState.COMPLETED,
    )

    return {
        "type": "completed",
    }


# Paging bookkeeping, not part of the complaint record.
INTERNAL_KEYS = ("local_body_offset",)


def get_completed_complaint(
    user_id: str,
) -> dict:
    """Collect the finished complaint for a user.

    Args:
        user_id: The user's phone number.

    Returns:
        A dictionary of everything the user has provided, without
        internal paging keys, plus the user's 'language'.
    """

    complaint = {
        key: value
        for key, value in get_data(user_id).items()
        if key not in INTERNAL_KEYS
    }

    complaint["language"] = language_of(user_id)

    return complaint


def localised_complaint(
    language: str,
    choice: str | None,
) -> str:
    """The chosen complaint's wording in the citizen's own language.

    Args:
        language: The language code to use.
        choice: The menu number that was chosen, if any.

    Returns:
        The localised description, or an empty string if unknown.
    """

    if not choice:
        return ""

    row_id = f"complaint_{choice}"

    for row in messages.menu(language)["rows"]:
        if row["id"] == row_id:
            return row.get("description") or row["title"]

    return ""


def build_receipt(
    language: str,
    reference: str,
    complaint: dict,
    has_officer: bool = True,
) -> str:
    """Compose the confirmation a citizen gets once a complaint is filed.

    Args:
        language: The language code to write the receipt in.
        reference: The complaint's reference number.
        complaint: The saved complaint fields.
        has_officer: False if no officer is listed for the local body.

    Returns:
        The message body, ready to send.
    """

    what = complaint.get("custom_complaint") or ""

    if not what:
        what = localised_complaint(
            language,
            complaint.get("complaint_choice"),
        ) or complaint.get("complaint_type", "")

    lines = [
        messages.t(language, "receipt_title"),
        messages.t(language, "receipt_reference").format(
            reference=reference,
        ),
        "",
        what,
    ]

    local_body = complaint.get("local_body")
    ward = complaint.get("ward_number")

    if local_body and ward:
        lines.append(
            messages.t(language, "receipt_where").format(
                local_body=local_body,
                ward=ward,
            )
        )

    lines.append("")
    lines.append(
        messages.t(
            language,
            "receipt_next" if has_officer else "receipt_no_officer",
        )
    )

    return "\n".join(lines)
