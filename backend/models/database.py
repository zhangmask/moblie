from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from backend.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class InstanceRecord(Base):
    __tablename__ = "instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_pubkey: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    provider_name: Mapped[str] = mapped_column("provider", String(20), nullable=False)
    provider_instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_ref: Mapped[str] = mapped_column("image_id", String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="creating", nullable=False)
    public_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    private_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    owner_wallet: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_wallet: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_os_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    instance_type: Mapped[str] = mapped_column(String(40), default="standard.small", nullable=False)
    network_ref: Mapped[str | None] = mapped_column("subnet_id", String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    instance_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImageWorkflowRecord(Base):
    __tablename__ = "image_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    requester_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    publisher_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_image_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_image_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    created_image_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UserImageRecord(Base):
    __tablename__ = "user_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(32), nullable=False)
    image_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    image_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_workflow_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_image_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="available", nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentOsRecord(Base):
    __tablename__ = "agent_os"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    publisher_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    agent_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skill: Mapped[str] = mapped_column(String(255), nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(32), default="hourly", nullable=False)
    price_amount: Mapped[str] = mapped_column(String(32), default="0", nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="SOL", nullable=False)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="published", nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PaymentOrderRecord(Base):
    __tablename__ = "payment_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    agent_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    agent_os_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    job_pubkey: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[str] = mapped_column(String(32), nullable=False)
    frozen_amount: Mapped[str | None] = mapped_column(String(32), nullable=True)
    settled_amount: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(16), default="SOL", nullable=False)
    chain_name: Mapped[str] = mapped_column(String(32), default="solana", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    transaction_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssetFileRecord(Base):
    __tablename__ = "asset_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    target_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    instance_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    reviewer_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    dimensions_json: Mapped[dict] = mapped_column("dimensions", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SettlementRecord(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    instance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    owner_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    publisher_wallet: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    platform_fee: Mapped[str] = mapped_column(String(32), default="0", nullable=False)
    publisher_amount: Mapped[str] = mapped_column(String(32), default="0", nullable=False)
    refunded_amount: Mapped[str] = mapped_column(String(32), default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="settled", nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, future=True, connect_args=_connect_args(settings.database_url))


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
