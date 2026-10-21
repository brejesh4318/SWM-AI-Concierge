# -*- coding: utf-8 -*-
"""Telling officers about complaints and handling their replies."""

import re
import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.complaints import (
    complaint_by_reference,
    mark_resolved,
    pending_for_officer,
)
from app.db.models import Complaint, Officer
from app.services import messages
from app.services.storage import save_whatsapp_photo
from app.state.conversation_state import ConversationState
from app.services.whatsapp_service import (
    send_image_message,
    send_text_message,
)

REFERENCE_PATTERN = re.compile(r"NLG-\d{4}-\d{5}", re.IGNORECASE)


def is_officer_reply(message: dict, state: ConversationState) -> bool:
    """Decide whether an officer's message is a resolution, not a new complaint.

    A reference number in the text or caption always counts. A photo counts
    unless the sender is mid-complaint and being asked for a photo.

    Args:
        message: The WhatsApp message object.
        state: The sender's current chatbot state.

    Returns:
        True if the officer handler should take the message.
    """

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


async def notify_officer(officer: Officer, complaint: Complaint) -> None:
    """Send a new complaint to its officer on WhatsApp.

    Failures are printed, not raised, so the citizen's receipt still goes out.

    Args:
        officer: The officer assigned to the complaint.
        complaint: The saved complaint.
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
        await send_text_message(officer.phone, "\n".join(lines))
    except Exception:
        traceback.print_exc()


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

    if match:
        complaint = await complaint_by_reference(
            session, match.group(0), officer.id
        )

        if complaint is None:
            await send_text_message(
                officer.phone,
                f"{match.group(0).upper()} is not assigned to you.",
            )
            return
    else:
        pending = await pending_for_officer(session, officer.id)

        if media_id is None or not pending:
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
            await send_text_message(
                officer.phone,
                "You have several pending complaints. Send the photo "
                "again with the reference number in the caption:\n"
                + "\n".join(c.reference_no for c in pending),
            )
            return

        complaint = pending[0]

    if complaint.officer_status == "resolved":
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
            traceback.print_exc()
            photo_path = media_id

    await mark_resolved(session, complaint, photo_path)

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
        traceback.print_exc()
