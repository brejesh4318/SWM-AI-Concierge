# -*- coding: utf-8 -*-
"""Read-only endpoints that feed the admin dashboard."""

import logging
import secrets

import httpx
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import Text, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Base, Complaint, ConversationStateRow, Officer
from app.db.session import get_session
from app.services.storage import BUCKET, SUPABASE_KEY, SUPABASE_PROJECT_URL

logger = logging.getLogger(__name__)


async def require_admin(x_admin_token: str | None = Header(default=None)):
    """Reject requests that lack the admin token, when one is configured.

    Args:
        x_admin_token: Value of the X-Admin-Token request header.

    Raises:
        HTTPException: 401 if ADMIN_TOKEN is set and the header differs.
    """

    expected = get_settings().ADMIN_TOKEN

    if expected and not secrets.compare_digest(
        x_admin_token or "", expected
    ):
        logger.warning("Admin request rejected: invalid token")
        raise HTTPException(status_code=401, detail="Invalid admin token")


router = APIRouter(
    prefix="/admin/api",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _rows(result) -> list[dict]:
    """Turn a result of (label, count) rows into JSON-ready dicts."""

    return [
        {"label": label or "Unknown", "count": count}
        for label, count in result.all()
    ]


@router.get("/auth")
async def auth_status():
    """Confirm the supplied token is accepted (the guard does the work)."""

    return {"ok": True}


@router.get("/photo-url")
async def photo_url(
    path: str,
    session: AsyncSession = Depends(get_session),
):
    """Sign a short-lived URL for a stored complaint or resolution photo.

    Only paths recorded on a complaint are signed, so this cannot be used
    to read other objects in the bucket.

    Args:
        path: Object path from photo_url or resolved_photo_url.
        session: Database session.

    Returns:
        A dict with the signed ``url``.

    Raises:
        HTTPException: 404 if no complaint holds the path, 502 if
            Supabase refuses to sign it.
    """

    known = await session.scalar(
        select(Complaint.id)
        .where(
            or_(
                Complaint.photo_url == path,
                Complaint.resolved_photo_url == path,
            )
        )
        .limit(1)
    )

    if known is None:
        logger.warning("Refused to sign unknown photo path %s", path)
        raise HTTPException(status_code=404, detail="Unknown photo")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPABASE_PROJECT_URL}/storage/v1/object/sign/{BUCKET}/{path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY or "",
            },
            json={"expiresIn": 3600},
        )

    if response.status_code != 200:
        logger.error(
            "Supabase refused to sign %s: %s %s",
            path,
            response.status_code,
            response.text,
        )
        raise HTTPException(status_code=502, detail="Could not sign photo")

    signed = response.json()["signedURL"].lstrip("/")

    return {"url": f"{SUPABASE_PROJECT_URL}/storage/v1/{signed}"}


@router.get("/summary")
async def summary(session: AsyncSession = Depends(get_session)):
    """Headline numbers and breakdowns for the overview page.

    Returns:
        Totals, status and officer-status splits, breakdowns by type,
        local body, language and local body type, a 30-day daily series,
        and the average hours taken to resolve a complaint.
    """

    now = datetime.now(timezone.utc)

    total = await session.scalar(select(func.count(Complaint.id))) or 0

    async def count_where(*conditions) -> int:
        return (
            await session.scalar(
                select(func.count(Complaint.id)).where(*conditions)
            )
            or 0
        )

    resolved = await count_where(Complaint.officer_status == "resolved")
    unassigned = await count_where(Complaint.officer_id.is_(None))
    last_24h = await count_where(
        Complaint.created_at >= now - timedelta(hours=24)
    )
    last_7d = await count_where(
        Complaint.created_at >= now - timedelta(days=7)
    )
    with_photo = await count_where(Complaint.photo_url.is_not(None))
    with_gps = await count_where(Complaint.latitude.is_not(None))

    avg_seconds = await session.scalar(
        select(
            func.avg(
                func.extract(
                    "epoch", Complaint.resolved_at - Complaint.created_at
                )
            )
        ).where(Complaint.resolved_at.is_not(None))
    )

    def breakdown(column, limit: int | None = None):
        query = (
            select(column, func.count(Complaint.id).label("n"))
            .group_by(column)
            .order_by(text("n DESC"))
        )

        return query.limit(limit) if limit else query

    by_day = await session.execute(
        select(
            func.date_trunc("day", Complaint.created_at).label("day"),
            func.count(Complaint.id),
        )
        .where(Complaint.created_at >= now - timedelta(days=30))
        .group_by("day")
        .order_by("day")
    )

    in_progress = await session.scalar(
        select(func.count()).select_from(ConversationStateRow)
    )

    officers_active = await session.scalar(
        select(func.count(Officer.id)).where(Officer.is_active.is_(True))
    )

    return {
        "totals": {
            "complaints": total,
            "pending": total - resolved,
            "resolved": resolved,
            "unassigned": unassigned,
            "last_24h": last_24h,
            "last_7d": last_7d,
            "with_photo": with_photo,
            "with_gps": with_gps,
            "resolution_rate": round(resolved / total * 100, 1)
            if total
            else 0,
            "avg_resolution_hours": round(avg_seconds / 3600, 1)
            if avg_seconds is not None
            else None,
            "active_officers": officers_active or 0,
            "open_conversations": in_progress or 0,
        },
        "by_status": _rows(await session.execute(breakdown(Complaint.status))),
        "by_type": _rows(
            await session.execute(breakdown(Complaint.complaint_type, 10))
        ),
        "by_local_body": _rows(
            await session.execute(breakdown(Complaint.local_body, 10))
        ),
        "pending_by_local_body": _rows(
            await session.execute(
                breakdown(Complaint.local_body, 10).where(
                    Complaint.officer_status == "pending"
                )
            )
        ),
        "pending_by_block": _rows(
            await session.execute(
                breakdown(Complaint.local_body_block, 10).where(
                    Complaint.officer_status == "pending"
                )
            )
        ),
        "by_local_body_type": _rows(
            await session.execute(breakdown(Complaint.local_body_type))
        ),
        "by_language": _rows(
            await session.execute(breakdown(Complaint.language))
        ),
        "by_day": [
            {"label": day.date().isoformat(), "count": count}
            for day, count in by_day.all()
        ],
    }


def _complaint(row: Complaint, officer_name: str | None) -> dict:
    """Serialise a complaint row for the table."""

    return {
        "id": row.id,
        "reference_no": row.reference_no,
        "phone_number": row.phone_number,
        "customer_name": row.customer_name,
        "language": row.language,
        "complaint_type": row.complaint_type,
        "custom_complaint": row.custom_complaint,
        "local_body_type": row.local_body_type,
        "local_body_block": row.local_body_block,
        "local_body": row.local_body,
        "ward_number": row.ward_number,
        "location_text": row.location_text,
        "latitude": float(row.latitude) if row.latitude is not None else None,
        "longitude": float(row.longitude)
        if row.longitude is not None
        else None,
        "photo_url": row.photo_url,
        "status": row.status,
        "officer_status": row.officer_status,
        "officer_id": row.officer_id,
        "officer_name": officer_name,
        "created_at": row.created_at,
        "assigned_at": row.assigned_at,
        "resolved_at": row.resolved_at,
        "resolved_photo_url": row.resolved_photo_url,
    }


@router.get("/complaints")
async def complaints(
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
    local_body: str | None = None,
    complaint_type: str | None = None,
    language: str | None = None,
    local_body_type: str | None = None,
    local_body_block: str | None = None,
    unassigned: bool = False,
    has_photo: bool = False,
    has_gps: bool = False,
    since_hours: int | None = Query(None, ge=1),
    day: date | None = None,
    search: str | None = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Page through complaints, newest first, with optional filters.

    Args:
        session: Database session.
        status: Match the officer status (pending / resolved).
        local_body: Exact local body name.
        complaint_type: Exact complaint type.
        language: Exact language code.
        local_body_type: municipality / town / village.
        local_body_block: Exact block name.
        unassigned: Only complaints with no officer.
        has_photo: Only complaints with a photo.
        has_gps: Only complaints with a GPS pin.
        since_hours: Only complaints filed within this many hours.
        day: Only complaints filed on this calendar day.
        search: Substring of reference, phone, name, location or details.
        limit: Page size.
        offset: Rows to skip.

    Returns:
        The matching total, the page of items, and the filter choices.
    """

    conditions = []

    if status:
        conditions.append(Complaint.officer_status == status)

    if local_body:
        conditions.append(Complaint.local_body == local_body)

    if complaint_type:
        conditions.append(Complaint.complaint_type == complaint_type)

    if language:
        conditions.append(Complaint.language == language)

    if local_body_type:
        conditions.append(Complaint.local_body_type == local_body_type)

    if local_body_block:
        conditions.append(Complaint.local_body_block == local_body_block)

    if unassigned:
        conditions.append(Complaint.officer_id.is_(None))

    if has_photo:
        conditions.append(Complaint.photo_url.is_not(None))

    if has_gps:
        conditions.append(Complaint.latitude.is_not(None))

    if since_hours:
        conditions.append(
            Complaint.created_at
            >= datetime.now(timezone.utc) - timedelta(hours=since_hours)
        )

    if day:
        conditions.append(func.date(Complaint.created_at) == day)

    if search:
        like = f"%{search}%"
        conditions.append(
            or_(
                Complaint.reference_no.ilike(like),
                Complaint.phone_number.ilike(like),
                Complaint.customer_name.ilike(like),
                Complaint.location_text.ilike(like),
                Complaint.custom_complaint.ilike(like),
            )
        )

    total = await session.scalar(
        select(func.count(Complaint.id)).where(*conditions)
    )

    rows = await session.execute(
        select(Complaint, Officer.name)
        .outerjoin(Officer, Officer.id == Complaint.officer_id)
        .where(*conditions)
        .order_by(Complaint.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    local_bodies = await session.scalars(
        select(Complaint.local_body)
        .where(Complaint.local_body.is_not(None))
        .distinct()
        .order_by(Complaint.local_body)
    )
    types = await session.scalars(
        select(Complaint.complaint_type).distinct().order_by(
            Complaint.complaint_type
        )
    )

    return {
        "total": total or 0,
        "items": [_complaint(c, name) for c, name in rows.all()],
        "filters": {
            "local_bodies": list(local_bodies),
            "types": [t for t in types if t],
        },
    }


@router.get("/officers")
async def officers(session: AsyncSession = Depends(get_session)):
    """List officers with how many complaints each holds."""

    pending = func.count(Complaint.id).filter(
        Complaint.officer_status == "pending"
    )
    resolved = func.count(Complaint.id).filter(
        Complaint.officer_status == "resolved"
    )

    rows = await session.execute(
        select(Officer, pending, resolved)
        .outerjoin(Complaint, Complaint.officer_id == Officer.id)
        .group_by(Officer.id)
        .order_by(Officer.local_body)
    )

    names = {
        o.id: o.name for o in await session.scalars(select(Officer))
    }

    return [
        {
            "id": o.id,
            "name": o.name,
            "phone": o.phone,
            "local_body": o.local_body,
            "escalation_officer": names.get(o.escalation_officer_id),
            "is_active": o.is_active,
            "created_at": o.created_at,
            "pending": p,
            "resolved": r,
        }
        for o, p, r in rows.all()
    ]


@router.get("/conversations")
async def conversations(session: AsyncSession = Depends(get_session)):
    """List citizens currently part-way through the WhatsApp flow."""

    rows = await session.scalars(
        select(ConversationStateRow).order_by(
            ConversationStateRow.updated_at.desc()
        )
    )

    return [
        {
            "phone_number": r.phone_number,
            "state": r.state,
            "language": r.language,
            "data": r.data,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.get("/tables")
async def tables(session: AsyncSession = Depends(get_session)):
    """Describe each database table: columns, keys and row count."""

    result = []

    for table in Base.metadata.sorted_tables:
        count = await session.scalar(
            select(func.count()).select_from(table)
        )

        result.append(
            {
                "name": table.name,
                "rows": count or 0,
                "columns": [
                    {
                        "name": c.name,
                        "type": str(c.type),
                        "nullable": c.nullable,
                        "primary_key": c.primary_key,
                        "unique": bool(c.unique),
                        "indexed": bool(c.index),
                        "foreign_key": ", ".join(
                            fk.target_fullname for fk in c.foreign_keys
                        )
                        or None,
                    }
                    for c in table.columns
                ],
            }
        )

    return result


@router.get("/tables/{name}")
async def table_rows(
    name: str,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
):
    """Return the latest rows of one table for inspection.

    Args:
        name: A table name from Base.metadata (anything else is a 404).
        session: Database session.
        limit: Maximum rows to return.
    """

    table = Base.metadata.tables.get(name)

    if table is None:
        raise HTTPException(status_code=404, detail="Unknown table")

    order = (
        table.c.created_at.desc()
        if "created_at" in table.c
        else table.c.updated_at.desc()
        if "updated_at" in table.c
        else None
    )

    query = select(*[cast(c, Text).label(c.name) for c in table.columns])

    if order is not None:
        query = query.order_by(order)

    rows = await session.execute(query.limit(limit))

    return {
        "columns": [c.name for c in table.columns],
        "rows": [list(r) for r in rows.all()],
    }
