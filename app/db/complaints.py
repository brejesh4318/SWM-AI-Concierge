# -*- coding: utf-8 -*-
"""Saving a finished complaint and giving it a reference number."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Complaint


REFERENCE_PREFIX = "NLG"


async def next_reference(
    session: AsyncSession,
    now: datetime | None = None,
) -> str:
    """Build the next reference number for the current year.

    Numbering restarts each year: NLG-2026-00001, NLG-2026-00002, ...

    Args:
        session: An open database session.
        now: Override for the current time, used by tests.

    Returns:
        The reference string for the complaint about to be created.
    """

    moment = now or datetime.now(timezone.utc)

    year = moment.year

    prefix = f"{REFERENCE_PREFIX}-{year}-"

    used = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.reference_no.startswith(prefix))
    )

    return f"{prefix}{(used or 0) + 1:05d}"


def _number(value) -> float | None:
    """Coerce a latitude or longitude to a float, or None."""

    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def save_complaint(
    session: AsyncSession,
    complaint: dict,
    wamid: str | None = None,
) -> Complaint:
    """Store a finished complaint and return the saved row.

    Args:
        session: An open database session.
        complaint: The dictionary from get_completed_complaint().
        wamid: The WhatsApp id of the message that completed the
            complaint, used to ignore repeated deliveries.

    Returns:
        The persisted Complaint, with its reference number set.
    """

    row = Complaint(
        reference_no=await next_reference(session),
        wamid=wamid,
        phone_number=complaint.get("phone_number", ""),
        customer_name=complaint.get("customer_name"),
        language=complaint.get("language", "en"),
        complaint_type=complaint.get("complaint_type", ""),
        custom_complaint=complaint.get("custom_complaint"),
        local_body_type=complaint.get("local_body_type"),
        local_body_block=complaint.get("local_body_block"),
        local_body=complaint.get("local_body"),
        ward_number=complaint.get("ward_number"),
        location_text=complaint.get("location_text"),
        latitude=_number(complaint.get("latitude")),
        longitude=_number(complaint.get("longitude")),
        photo_url=complaint.get("photo_media_id"),
        status="new",
    )

    session.add(row)

    await session.flush()

    return row


async def already_saved(
    session: AsyncSession,
    wamid: str | None,
) -> Complaint | None:
    """Find a complaint already filed from this WhatsApp message.

    Meta re-delivers a webhook if it does not get a prompt 200, so the
    same completing message can arrive twice.

    Args:
        session: An open database session.
        wamid: The WhatsApp message id, or None.

    Returns:
        The existing Complaint, or None.
    """

    if not wamid:
        return None

    return await session.scalar(
        select(Complaint).where(Complaint.wamid == wamid)
    )
