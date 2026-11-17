import os

# Must be set before any app module is imported.
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ["VERIFY_TOKEN"] = "verify-me"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, Complaint, Officer
from app.state import conversation_manager as cm


@pytest.fixture(autouse=True)
def clean_conversations():
    """Reset the in-memory conversation stores around every test."""
    for store in (
        cm.conversation_states,
        cm.conversation_data,
        cm.conversation_language,
    ):
        store.clear()
    yield
    for store in (
        cm.conversation_states,
        cm.conversation_data,
        cm.conversation_language,
    ):
        store.clear()


@pytest_asyncio.fixture
async def session():
    """An in-memory SQLite session holding the officers/complaints tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[Officer.__table__, Complaint.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def officer(session):
    row = Officer(name="Ravi", phone="919800000001", local_body="Coonoor")
    session.add(row)
    await session.commit()
    return row


def make_complaint_dict(**over):
    data = {
        "phone_number": "919811111111",
        "customer_name": "Asha",
        "language": "en",
        "complaint_type": "Other",
        "local_body": "Coonoor",
        "local_body_type": "municipality",
        "local_body_block": "Coonoor",
        "ward_number": "4",
        "location_text": "Main road",
        "latitude": "11.35",
        "longitude": "76.79",
    }
    data.update(over)
    return data
