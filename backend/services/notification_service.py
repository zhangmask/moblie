from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.cloud.contracts.notification import NotificationMessage, NotificationPort
from backend.models.database import NotificationRecord
from backend.models.schemas import NotificationEvent


class NotificationService(NotificationPort):
    def __init__(self, channels: dict[str, object] | None = None) -> None:
        self.channels = channels or {}

    async def publish(
        self,
        db: Session,
        wallet: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> NotificationEvent:
        message = NotificationMessage(
            channel="websocket",
            target=wallet,
            event_type=event_type,
            payload=payload,
        )
        return await self.send(message, db=db)

    async def send(
        self,
        message: NotificationMessage,
        db: Session | None = None,
    ) -> NotificationEvent:
        if db is None:
            raise ValueError("NotificationService.send 需要提供数据库会话")
        channel = self.channels.get(message.channel)
        record = NotificationRecord(
            wallet=message.target,
            type=message.event_type,
            payload=message.payload,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        event = self._to_schema(record)
        if channel and hasattr(channel, "send"):
            await channel.send(message)
        return event

    async def connect(self, wallet: str, websocket) -> None:
        channel = self.channels.get("websocket")
        if channel and hasattr(channel, "connect"):
            await channel.connect(wallet, websocket)

    def disconnect(self, wallet: str, websocket) -> None:
        channel = self.channels.get("websocket")
        if channel and hasattr(channel, "disconnect"):
            channel.disconnect(wallet, websocket)

    def list_recent(self, db: Session, wallet: str, limit: int = 20) -> list[NotificationEvent]:
        stmt = (
            select(NotificationRecord)
            .where(NotificationRecord.wallet == wallet)
            .order_by(desc(NotificationRecord.created_at))
            .limit(limit)
        )
        records = db.scalars(stmt).all()
        return [self._to_schema(record) for record in records]

    @staticmethod
    def _to_schema(record: NotificationRecord) -> NotificationEvent:
        return NotificationEvent(
            id=record.id,
            wallet=record.wallet,
            type=record.type,
            payload=record.payload,
            read=bool(record.read),
            created_at=record.created_at,
        )
