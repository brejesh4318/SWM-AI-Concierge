# -*- coding: utf-8 -*-
"""Saving a finished complaint and giving it a reference number."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Complaint, Officer


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

    officer = await officer_for(session, row)

    if officer is not None:
        row.officer_id = officer.id
        row.assigned_at = datetime.now(timezone.utc)

    return row


async def officer_for(
    session: AsyncSession,
    complaint: Complaint,
) -> Officer | None:
    """Find the officer currently responsible for a complaint.

    Complaints and officers are linked by local body name, not by a
    foreign key, so this always returns whoever holds that local body now.

    Args:
        session: An open database session.
        complaint: The saved complaint.

    Returns:
        The active Officer for the complaint's local body, or None.
    """

    if not complaint.local_body:
        return None

    return await session.scalar(
        select(Officer)
        .join(Complaint, Complaint.local_body == Officer.local_body)
        .where(
            Complaint.id == complaint.id,
            Officer.is_active.is_(True),
        )
    )


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


async def officer_by_phone(
    session: AsyncSession,
    phone: str,
) -> Officer | None:
    """Find the active officer who owns a WhatsApp number.

    Args:
        session: An open database session.
        phone: The sender's number, digits only.

    Returns:
        The active Officer with that number, or None.
    """

    return await session.scalar(
        select(Officer).where(
            Officer.phone == phone,
            Officer.is_active.is_(True),
        )
    )


async def pending_for_officer(
    session: AsyncSession,
    officer_id: int,
) -> list[Complaint]:
    """List an officer's complaints that are still unresolved, oldest first.

    Args:
        session: An open database session.
        officer_id: The officer's id.

    Returns:
        The pending Complaint rows.
    """

    result = await session.scalars(
        select(Complaint)
        .where(
            Complaint.officer_id == officer_id,
            Complaint.officer_status == "pending",
        )
        .order_by(Complaint.created_at)
    )

    return list(result)


async def complaint_by_reference(
    session: AsyncSession,
    reference_no: str,
    officer_id: int,
) -> Complaint | None:
    """Find one of an officer's complaints by reference number.

    Args:
        session: An open database session.
        reference_no: For example NLG-2026-00001.
        officer_id: Only complaints assigned to this officer match.

    Returns:
        The Complaint, or None.
    """

    return await session.scalar(
        select(Complaint).where(
            Complaint.reference_no == reference_no.upper(),
            Complaint.officer_id == officer_id,
        )
    )


async def mark_resolved(
    session: AsyncSession,
    complaint: Complaint,
    photo_path: str | None,
) -> Complaint:
    """Record that the officer has resolved a complaint.

    Args:
        session: An open database session.
        complaint: The complaint being resolved.
        photo_path: Storage path of the officer's proof photo, if any.

    Returns:
        The updated Complaint.
    """

    complaint.officer_status = "resolved"
    complaint.status = "resolved"
    complaint.resolved_at = datetime.now(timezone.utc)
    complaint.resolved_photo_url = photo_path

    await session.commit()

    return complaint
