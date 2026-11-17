# -*- coding: utf-8 -*-
import json
import logging
import os
import uuid

import httpx
from dotenv import load_dotenv

from app.core.logging import mask_phone,timed
from app.services import local_bodies, messages

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Approved template used to alert an officer who has not messaged the bot
# in the last 24 hours. See the README for the body it must have.
OFFICER_TEMPLATE_NAME = os.getenv(
    "OFFICER_TEMPLATE_NAME", "new_complaint_alert"
)
OFFICER_TEMPLATE_LANG = os.getenv("OFFICER_TEMPLATE_LANG", "en")

WHATSAPP_API_URL = (
    f"https://graph.facebook.com/v26.0/"
    f"{PHONE_NUMBER_ID}/messages"
)

# When true, outgoing messages are logged instead of sent, so the bot can
# be exercised without a working WhatsApp account.
DRY_RUN = os.getenv("WHATSAPP_DRY_RUN", "").lower() in ("1", "true", "yes")


async def _send_whatsapp_payload(payload: dict) -> dict:
    """Post a message payload to the WhatsApp Cloud API.

    Args:
        payload: The full message body to send.

    Returns:
        The parsed JSON response from the API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """
    kind = payload.get("type")
    recipient = mask_phone(payload.get("to"))

    if DRY_RUN:
        logger.info(
            "WhatsApp DRY RUN, not sending %s to %s: %s",
            kind,
            recipient,
            json.dumps(payload, ensure_ascii=False),
        )
        return {"messages": [{"id": f"wamid.DRYRUN{uuid.uuid4().hex}"}]}

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            with timed(f"meta_send_{kind}"):
                response = await client.post(
                WHATSAPP_API_URL,
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError:
        logger.exception(
            "WhatsApp send of %s to %s failed before a response",
            kind,
            recipient,
        )
        raise

    if response.is_error:
        logger.error(
            "WhatsApp send of %s to %s failed: %s %s",
            kind,
            recipient,
            response.status_code,
            response.text,
        )
        response.raise_for_status()

    logger.info(
        "WhatsApp sent %s to %s (%s)",
        kind,
        recipient,
        response.status_code,
    )
    logger.debug("WhatsApp API response: %s", response.text)

    return response.json()


def _envelope(recipient_phone: str) -> dict:
    """Build the fields every outgoing WhatsApp message needs.

    Args:
        recipient_phone: The recipient's phone number.

    Returns:
        A dictionary holding the messaging product, recipient type and
        recipient number, ready to be extended with the message content.
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
    }


def _reply_buttons(buttons: list) -> list:
    """Convert button definitions into WhatsApp reply-button objects.

    Args:
        buttons: A list of dictionaries, each with an 'id' and a 'title'.

    Returns:
        A list of reply-button objects in the WhatsApp API format.
    """
    return [
        {
            "type": "reply",
            "reply": {
                "id": button["id"],
                "title": button["title"],
            },
        }
        for button in buttons
    ]


async def send_text_message(
    recipient_phone: str,
    message: str,
) -> dict:
    """Send a plain text message.

    Args:
        recipient_phone: The recipient's phone number.
        message: The text to send.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "text",
            "text": {
                "body": message,
            },
        }
    )

    return await _send_whatsapp_payload(payload)


def message_id_of(response: dict) -> str | None:
    """Pull the sent message's id out of a send response.

    Args:
        response: The parsed JSON returned by a send call.

    Returns:
        The wamid, or None if the response has no message.
    """

    try:
        return response["messages"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return None


async def send_template_message(
    recipient_phone: str,
    name: str,
    language_code: str,
    body_params: list[str],
) -> dict:
    """Send an approved message template.

    Unlike free-form text, a template can start a conversation outside
    WhatsApp's 24-hour window.

    Args:
        recipient_phone: The recipient's phone number.
        name: The template's name as approved in Meta Business Manager.
        language_code: The template's language, such as "en".
        body_params: Values for {{1}}, {{2}}... in the template body, in
            order. Newlines are flattened and blanks become "-" because
            WhatsApp rejects both.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "template",
            "template": {
                "name": name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": " ".join(str(value).split()) or "-",
                            }
                            for value in body_params
                        ],
                    }
                ],
            },
        }
    )

    return await _send_whatsapp_payload(payload)


async def send_language_menu(
    recipient_phone: str,
) -> dict:
    """Introduce Thuyan and ask for a language.

    This is the only screen that shows both languages, because the
    user has not chosen one yet.

    Args:
        recipient_phone: The recipient's phone number.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": messages.INTRO["body"],
                },
                "action": {
                    "buttons": _reply_buttons(
                        messages.INTRO["buttons"]
                    ),
                },
            },
        }
    )

    return await _send_whatsapp_payload(payload)


async def send_complaint_menu(
    recipient_phone: str,
    language: str,
) -> dict:
    """Send the list of complaint types to choose from.

    Args:
        recipient_phone: The recipient's phone number.
        language: The language code to show the menu in.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    menu = messages.menu(language)

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": menu["header"],
                },
                "body": {
                    "text": menu["body"],
                },
                "footer": {
                    "text": menu["footer"],
                },
                "action": {
                    "button": menu["button"],
                    "sections": [
                        {
                            "title": menu["section"],
                            "rows": menu["rows"],
                        }
                    ],
                },
            },
        }
    )

    return await _send_whatsapp_payload(payload)


async def send_photo_question(
    recipient_phone: str,
    language: str,
) -> dict:
    """Ask whether the user wants to attach a photo, with Yes/No buttons.

    Args:
        recipient_phone: The recipient's phone number.
        language: The language code to ask the question in.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    question = messages.photo_question(language)

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": question["body"],
                },
                "action": {
                    "buttons": _reply_buttons(
                        question["buttons"]
                    ),
                },
            },
        }
    )

    return await _send_whatsapp_payload(payload)


def _list_payload(
    recipient_phone: str,
    screen: dict,
    rows: list,
) -> dict:
    """Build an interactive list message from a screen and its rows.

    Args:
        recipient_phone: The recipient's phone number.
        screen: The header, body, footer, button and section texts.
        rows: The list rows to show.

    Returns:
        The message payload, ready to be sent.
    """

    payload = _envelope(recipient_phone)

    payload.update(
        {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": screen["header"],
                },
                "body": {
                    "text": screen["body"],
                },
                "footer": {
                    "text": screen["footer"],
                },
                "action": {
                    "button": screen["button"],
                    "sections": [
                        {
                            "title": screen["section"],
                            "rows": rows,
                        }
                    ],
                },
            },
        }
    )

    return payload


async def send_local_body_type_menu(
    recipient_phone: str,
    language: str,
) -> dict:
    """Send the list of local body types (municipality, town, village).

    Args:
        recipient_phone: The recipient's phone number.
        language: The language code to show the menu in.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    screen = messages.local_body(language)["type"]

    rows = [
        {
            "id": local_bodies.TYPE_ROW_IDS[key],
            "title": screen["labels"][key],
            "description": screen["descriptions"][key],
        }
        for key in local_bodies.TYPE_ORDER
    ]

    return await _send_whatsapp_payload(
        _list_payload(recipient_phone, screen, rows)
    )


async def send_block_menu(
    recipient_phone: str,
    language: str,
    body_type: str,
) -> dict:
    """Send the list of blocks that have local bodies of the given type.

    Args:
        recipient_phone: The recipient's phone number.
        language: The language code to show the menu in.
        body_type: The local body type key to list blocks for.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    screen = messages.local_body(language)["block"]

    rows = [
        {
            "id": local_bodies.BLOCK_ROW_IDS[block],
            "title": block,
        }
        for block in local_bodies.blocks(body_type)
    ]

    return await _send_whatsapp_payload(
        _list_payload(recipient_phone, screen, rows)
    )


async def send_local_body_menu(
    recipient_phone: str,
    language: str,
    body_type: str,
    block: str = "",
    offset: int = 0,
) -> dict:
    """One page of local bodies, with a "more" row if any are left.

    Args:
        recipient_phone: The recipient's phone number.
        language: The language code to show the menu in.
        body_type: The local body type key to list.
        block: Restrict the list to this block. Defaults to an empty
            string, meaning all blocks.
        offset: How many matching bodies to skip. Defaults to 0.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    screen = messages.local_body(language)["body"]

    indexes, next_offset = local_bodies.page(
        body_type,
        block,
        offset,
    )

    rows = [
        {
            "id": local_bodies.row_id(index),
            "title": local_bodies.get(index)["name"],
        }
        for index in indexes
    ]

    if next_offset is not None:
        rows.append(
            {
                "id": local_bodies.MORE_ID,
                "title": screen["more"],
                "description": screen["more_description"],
            }
        )

    return await _send_whatsapp_payload(
        _list_payload(recipient_phone, screen, rows)
    )


async def send_image_message(
    recipient_phone: str,
    media_id: str,
    caption: str | None = None,
) -> dict:
    """Send an image that is already uploaded to WhatsApp.

    Args:
        recipient_phone: The recipient's phone number.
        media_id: The WhatsApp media id of the image.
        caption: Optional text shown under the image.

    Returns:
        The parsed JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status.
    """

    image = {"id": media_id}

    if caption:
        image["caption"] = caption

    payload = _envelope(recipient_phone)

    payload.update({"type": "image", "image": image})

    return await _send_whatsapp_payload(payload)
