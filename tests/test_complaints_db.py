from datetime import datetime, timezone

from app.db import complaints as db
from tests.conftest import make_complaint_dict


async def test_next_reference_numbers_per_year(session):
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert await db.next_reference(session, now) == "NLG-2026-00001"
    await db.save_complaint(session, make_complaint_dict())
    await session.commit()
    year = datetime.now(timezone.utc).year
    assert (
        await db.next_reference(session)
    ) == f"NLG-{year}-00002"
    assert await db.next_reference(
        session, datetime(2030, 1, 1, tzinfo=timezone.utc)
    ) == "NLG-2030-00001"


def test_number_coercion():
    assert db._number(None) is None
    assert db._number("") is None
    assert db._number("abc") is None
    assert db._number("11.5") == 11.5
    assert db._number(3) == 3.0


async def test_save_complaint_without_officer(session):
    row = await db.save_complaint(
        session, make_complaint_dict(latitude="bad"), wamid="w1"
    )
    assert row.id is not None
    assert row.status == "new" and row.wamid == "w1"
    assert row.latitude is None
    assert row.officer_id is None and row.assigned_at is None


async def test_save_complaint_assigns_active_officer(session, officer):
    row = await db.save_complaint(session, make_complaint_dict())
    assert row.officer_id == officer.id
    assert row.assigned_at is not None


async def test_inactive_officer_not_assigned(session, officer):
    officer.is_active = False
    await session.commit()
    row = await db.save_complaint(session, make_complaint_dict())
    assert row.officer_id is None
    assert await db.officer_by_phone(session, officer.phone) is None


async def test_officer_for_without_local_body(session, officer):
    row = await db.save_complaint(
        session, make_complaint_dict(local_body=None)
    )
    assert await db.officer_for(session, row) is None


async def test_already_saved(session):
    assert await db.already_saved(session, None) is None
    assert await db.already_saved(session, "nope") is None
    row = await db.save_complaint(session, make_complaint_dict(), wamid="w9")
    await session.commit()
    assert (await db.already_saved(session, "w9")).id == row.id


async def test_officer_by_phone(session, officer):
    assert (await db.officer_by_phone(session, officer.phone)).id == officer.id
    assert await db.officer_by_phone(session, "000") is None


async def test_pending_and_lookup_queries(session, officer):
    a = await db.save_complaint(session, make_complaint_dict())
    b = await db.save_complaint(session, make_complaint_dict())
    other = await db.save_complaint(
        session, make_complaint_dict(local_body="Elsewhere")
    )
    a.notification_wamid = "wamid.A"
    await session.commit()

    pending = await db.pending_for_officer(session, officer.phone)
    assert {c.id for c in pending} == {a.id, b.id}
    assert other.id not in {c.id for c in pending}

    found = await db.complaint_by_reference(
        session, a.reference_no.lower(), officer.phone
    )
    assert found.id == a.id
    assert (
        await db.complaint_by_reference(session, a.reference_no, "999")
    ) is None
    assert (
        await db.complaint_by_reference(
            session, other.reference_no, officer.phone
        )
    ) is None

    assert (
        await db.complaint_by_notification(session, "wamid.A", officer.phone)
    ).id == a.id
    assert (
        await db.complaint_by_notification(session, "wamid.A", "999")
    ) is None


async def test_mark_resolved(session, officer):
    row = await db.save_complaint(session, make_complaint_dict())
    await db.mark_resolved(session, row, "resolved/x.jpeg")
    assert row.status == "resolved" and row.officer_status == "resolved"
    assert row.resolved_at is not None
    assert row.resolved_photo_url == "resolved/x.jpeg"
    assert await db.pending_for_officer(session, officer.phone) == []
