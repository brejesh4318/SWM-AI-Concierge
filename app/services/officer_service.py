# -*- coding: utf-8 -*-
"""Telling officers about complaints and handling their replies."""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import mask_phone
from app.db.complaints import (
    complaint_by_notification,
    complaint_by_reference,
    mark_resolved,
    pending_for_officer,
)
from app.db.models import Complaint, Officer
from app.services import messages
from app.services.storage import save_whatsapp_photo
from app.state.conversation_state import ConversationState
from app.services.whatsapp_service import (
    OFFICER_TEMPLATE_LANG,
    OFFICER_TEMPLATE_NAME,
    message_id_of,
    send_image_message,
    send_template_message,
    send_text_message,
)

logger = logging.getLogger(__name__)

REFERENCE_PATTERN = re.compile(r"NLG-\d{4}-\d{5}", re.IGNORECASE)


async def is_officer_reply(
    session: AsyncSession,
    officer: Officer,
    message: dict,
    state: ConversationState,
) -> bool:
    """Decide whether an officer's message is a resolution, not a new complaint.

    A swipe-reply to one of the officer's complaint alerts always counts,
    with or without a photo. So does a reference number in the text or
    caption. A photo counts unless the sender is mid-complaint and being
    asked for a photo.

    Args:
        session: An open database session.
        officer: The officer who sent the message.
        message: The WhatsApp message object.
        state: The sender's current chatbot state.

    Returns:
        True if the officer handler should take the message.
    """

    replied_to = (message.get("context") or {}).get("id")

    if replied_to and await complaint_by_notification(
        session, replied_to, officer.phone
    ):
        return True

    kind = message.get("type")

    if kind == "text":
        text = message["text"]["body"]
    elif kind == "image":
        text = message.get("image", {}).get("caption") or ""
    else:
        return False

    if REFERENCE_PATTERN.search(text):
        return True

    return kind == "image" and state != ConversationState.WAITING_FOR_PHOTO


async def notify_officer(
    officer: Officer,
    complaint: Complaint,
) -> str | None:
    """Send a new complaint to its officer on WhatsApp.

    Sends plain text, and falls back to an approved template if WhatsApp
    refuses it (the officer is outside the 24-hour window). Failures are
    printed, not raised, so the citizen's receipt still goes out.

    Args:
        officer: The officer assigned to the complaint.
        complaint: The saved complaint.

    Returns:
        The WhatsApp id of the alert, or None if nothing was delivered.
    """

    lines = [
        f"🆕 *New complaint {complaint.reference_no}*",
        f"Type: {complaint.complaint_type}",
    ]

    if complaint.custom_complaint:
        lines.append(f"Details: {complaint.custom_complaint}")

    lines.append(
        f"Area: {complaint.local_body}, Ward {complaint.ward_number}"
    )

    if complaint.location_text:
        lines.append(f"Location: {complaint.location_text}")

    if complaint.latitude is not None and complaint.longitude is not None:
        lines.append(
            "Map: https://maps.google.com/?q="
            f"{complaint.latitude},{complaint.longitude}"
        )

    if complaint.customer_name:
        lines.append(f"Raised by: {complaint.customer_name}")

    lines.append(
        f"\nWhen resolved, reply with a *photo* of the resolved issue "
        f"and put *{complaint.reference_no}* in the caption."
    )

    try:
        response = await send_text_message(officer.phone, "\n".join(lines))
        logger.info(
            "Officer %s notified of %s by text",
            mask_phone(officer.phone),
            complaint.reference_no,
        )
        return message_id_of(response)
    except Exception:
        # Free-form text is refused when the officer has not messaged the
        # bot in the last 24 hours, so retry with an approved template.
        logger.warning(
            "Text alert for %s to officer %s refused; trying the template",
            complaint.reference_no,
            mask_phone(officer.phone),
            exc_info=True,
        )

    map_link = (
        f"https://maps.google.com/?q={complaint.latitude},{complaint.longitude}"
        if complaint.latitude is not None and complaint.longitude is not None
        else complaint.location_text or "-"
    )

    try:
        response = await send_template_message(
            officer.phone,
            OFFICER_TEMPLATE_NAME,
            OFFICER_TEMPLATE_LANG,
            [
                complaint.reference_no,
                complaint.complaint_type,
                f"{complaint.local_body}, Ward {complaint.ward_number}",
                map_link,
            ],
        )
        logger.info(
            "Officer %s notified of %s by template",
            mask_phone(officer.phone),
            complaint.reference_no,
        )
        return message_id_of(response)
    except Exception:
        logger.exception(
            "OFFICER NOT NOTIFIED: %s -> %s",
            complaint.reference_no,
            mask_phone(officer.phone),
        )
        return None


async def handle_officer_message(
    session: AsyncSession,
    officer: Officer,
    message: dict,
) -> None:
    """Treat an officer's WhatsApp message as a reply to a complaint.

    A photo resolves the complaint named in its caption, or the officer's
    only pending complaint. A text reply resolves only when it names a
    reference number. The photo is forwarded to whoever raised it.

    Args:
        session: An open database session.
        officer: The officer who sent the message.
        message: The WhatsApp message object.
    """

    kind = message.get("type")

    if kind == "image":
        image = message.get("image", {})
        media_id = image.get("id")
        text = image.get("caption") or ""
    elif kind == "text":
        media_id = None
        text = message["text"]["body"]
    else:
        media_id = None
        text = ""

    match = REFERENCE_PATTERN.search(text)

    # A swipe-reply to the alert names its complaint without typing.
    replied_to = (message.get("context") or {}).get("id")

    complaint = None

    if match:
        complaint = await complaint_by_reference(
            session, match.group(0), officer.phone
        )

        if complaint is None:
            logger.warning(
                "Officer %s tried to resolve %s, which is not theirs",
                mask_phone(officer.phone),
                match.group(0).upper(),
            )
            await send_text_message(
                officer.phone,
                f"{match.group(0).upper()} is not assigned to you.",
            )
            return
    elif replied_to:
        complaint = await complaint_by_notification(
            session, replied_to, officer.phone
        )

    if complaint is None:
        pending = await pending_for_officer(session, officer.phone)

        if media_id is None or not pending:
            logger.info(
                "Officer %s sent no resolvable reply (%d pending)",
                mask_phone(officer.phone),
                len(pending),
            )
            await send_text_message(
                officer.phone,
                (
                    "No pending complaints."
                    if not pending
                    else "To resolve a complaint, send a photo with its "
                    "reference number in the caption.\nPending: "
                    + ", ".join(c.reference_no for c in pending)
                ),
            )
            return

        if len(pending) > 1:
            logger.info(
                "Officer %s has %d pending complaints; asking which one",
                mask_phone(officer.phone),
                len(pending),
            )
            await send_text_message(
                officer.phone,
                "You have several pending complaints. Send the photo "
                "again with the reference number in the caption:\n"
                + "\n".join(c.reference_no for c in pending),
            )
            return

        complaint = pending[0]

    if complaint.officer_status == "resolved":
        logger.info("%s was already resolved", complaint.reference_no)
        await send_text_message(
            officer.phone,
            f"{complaint.reference_no} is already marked resolved.",
        )
        return

    photo_path = None

    if media_id:
        try:
            photo_path = await save_whatsapp_photo(
                media_id, f"resolved/{complaint.reference_no}"
            )
        except Exception:
            logger.exception(
                "Could not store resolution photo for %s; keeping media id",
                complaint.reference_no,
            )
            photo_path = media_id

    await mark_resolved(session, complaint, photo_path)

    logger.info(
        "%s resolved by officer %s (photo=%s)",
        complaint.reference_no,
        mask_phone(officer.phone),
        photo_path is not None,
    )

    await send_text_message(
        officer.phone,
        f"✅ {complaint.reference_no} marked as resolved. Thank you.",
    )

    notice = messages.t(complaint.language, "resolved_notice").format(
        reference=complaint.reference_no
    )

    try:
        if media_id:
            await send_image_message(
                complaint.phone_number, media_id, caption=notice
            )
        else:
            await send_text_message(complaint.phone_number, notice)
    except Exception:
        logger.exception(
            "Could not tell citizen %s that %s is resolved",
            mask_phone(complaint.phone_number),
            complaint.reference_no,
        )
