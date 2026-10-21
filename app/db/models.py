from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_no: Mapped[str] = mapped_column(String(32), unique=True)
    wamid: Mapped[str | None] = mapped_column(String(128), unique=True)

    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    customer_name: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(5))

    complaint_type: Mapped[str] = mapped_column(String(200))
    custom_complaint: Mapped[str | None] = mapped_column(String(2000))

    local_body_type: Mapped[str | None] = mapped_column(String(20))
    local_body_block: Mapped[str | None] = mapped_column(String(50))
    local_body: Mapped[str | None] = mapped_column(String(80), index=True)
    ward_number: Mapped[str | None] = mapped_column(String(10))

    location_text: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    photo_url: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Officer handling this complaint, fixed when it is filed so later
    # changes to the local body's officer do not rewrite history.
    officer_id: Mapped[int | None] = mapped_column(
        ForeignKey("officers.id", ondelete="SET NULL"), index=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # "pending" until the officer replies, then "resolved".
    officer_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # Storage path of the officer's proof photo, sent back to phone_number.
    resolved_photo_url: Mapped[str | None] = mapped_column(String(500))


class Officer(Base):
    __tablename__ = "officers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    # WhatsApp format: country code + number, digits only (918098059300).
    phone: Mapped[str] = mapped_column(String(20))
    # Matches a name in app.services.local_bodies.BODIES.
    local_body: Mapped[str] = mapped_column(String(80), unique=True)
    escalation_officer_id: Mapped[int | None] = mapped_column(
        ForeignKey("officers.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConversationStateRow(Base):
    __tablename__ = "conversation_state"

    phone_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    state: Mapped[str] = mapped_column(String(40))
    language: Mapped[str | None] = mapped_column(String(5))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
