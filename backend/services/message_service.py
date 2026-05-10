from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import MessageRecord, UserImageRecord
from backend.models.schemas import ImageMessageCreateRequest, MessageResponse
from backend.services.notification_service import NotificationService


class MessageService:
    def __init__(self, notification_service: NotificationService) -> None:
        self.notification_service = notification_service

    async def send_image_message(
        self,
        db: Session,
        image: UserImageRecord,
        payload: ImageMessageCreateRequest,
    ) -> list[MessageResponse]:
        user_message = MessageRecord(
            owner_wallet=image.owner_wallet,
            target_type="image",
            target_id=image.id,
            role="user",
            content=payload.content,
            metadata_json=payload.metadata,
        )
        db.add(user_message)
        db.flush()

        assistant_message = MessageRecord(
            owner_wallet=image.owner_wallet,
            target_type="image",
            target_id=image.id,
            role="assistant",
            content=f"已收到针对镜像 `{image.image_name}` 的消息：{payload.content}",
            metadata_json={"mode": "demo_echo"},
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        await self.notification_service.publish(
            db,
            image.owner_wallet,
            "image_message_updated",
            {"image_id": image.id, "message_id": assistant_message.id},
        )
        return [self._to_schema(user_message), self._to_schema(assistant_message)]

    def list_image_messages(self, db: Session, image_id: str) -> list[MessageResponse]:
        stmt = (
            select(MessageRecord)
            .where(MessageRecord.target_type == "image", MessageRecord.target_id == image_id)
            .order_by(MessageRecord.created_at.asc())
        )
        return [self._to_schema(record) for record in db.scalars(stmt).all()]

    @staticmethod
    def _to_schema(record: MessageRecord) -> MessageResponse:
        return MessageResponse(
            id=record.id,
            owner_wallet=record.owner_wallet,
            target_type=record.target_type,
            target_id=record.target_id,
            role=record.role,
            content=record.content,
            metadata=record.metadata_json,
            created_at=record.created_at,
        )
