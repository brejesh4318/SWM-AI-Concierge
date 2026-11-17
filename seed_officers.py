"""Seed one test officer per local body.

Every officer gets the same test phone number. Safe to re-run: local
bodies that already have an officer are skipped.
"""
import asyncio

from sqlalchemy import select

from app.db.models import Officer
from app.db.session import SessionLocal, engine
from app.services.local_bodies import BODIES

TEST_PHONE = "918098059300"

NAMES = (
    "Arun Kumar", "Karthik Raja", "Suresh Babu", "Murugan Selvam",
    "Venkatesh Iyer", "Ramesh Naidu", "Senthil Nathan", "Prakash Rao",
    "Manikandan S", "Rajesh Pillai", "Anand Krishnan", "Vijay Shankar",
    "Dinesh Kannan", "Gopal Reddy", "Harish Menon", "Balaji Subramanian",
    "Naveen Chandran", "Sathish Kumar", "Ganesh Moorthy", "Ashok Varma",
    "Lakshmi Narayanan", "Priya Dharshini", "Meena Kumari", "Kavitha Rani",
    "Divya Bharathi", "Anitha Sundaram", "Revathi Nair", "Sangeetha Devi",
    "Deepa Lakshmi", "Nirmala Gowda", "Sudha Ramesh", "Vimala Joseph",
    "Jayanthi Raman", "Padma Venkat", "Radha Krishnan", "Saranya Mohan",
    "Thilaga Pandian", "Uma Maheswari", "Bhuvana Rajan", "Chitra Devi",
    "Mohan Das", "Ravi Chandran", "Sekar Palani", "Thangaraj M",
    "Selvakumar P", "Ilango Perumal", "Kumaresan V", "Jagadish Hegde",
    "Narasimha Murthy", "Basavaraj K",
)


async def main():
    """Insert a test officer for each local body that has none.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the database cannot be reached
            or the officers table does not exist yet.
    """
    assert len(NAMES) >= len(BODIES), "Add more names"
    async with SessionLocal() as session:
        existing = set(
            (await session.execute(select(Officer.local_body))).scalars()
        )
        added = 0
        for (body, _type, _block), name in zip(BODIES, NAMES):
            if body in existing:
                continue
            session.add(Officer(name=name, phone=TEST_PHONE, local_body=body))
            added += 1
        await session.commit()
    print(f"Added {added} officers ({len(existing)} already existed)")
    await engine.dispose()


asyncio.run(main())
