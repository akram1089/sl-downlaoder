import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    probing = "probing"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="user")
    cookie_profiles: Mapped[list["CookieProfile"]] = relationship(back_populates="user")


class CookieProfile(Base):
    __tablename__ = "cookie_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    encrypted_blob: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="cookie_profiles")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)
    extractor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    format_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_only: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    speed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    playlist_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cookie_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cookie_profiles.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    filepath: Mapped[str | None] = mapped_column(Text, nullable=True)
    filesize: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="jobs")
