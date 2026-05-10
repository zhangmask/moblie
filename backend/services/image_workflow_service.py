from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import ImageWorkflowRecord, UserImageRecord
from backend.models.schemas import (
    ImageWorkflowConfirmRequest,
    ImageWorkflowCreateRequest,
    ImageWorkflowResponse,
    UserImageResponse,
)
from backend.services.notification_service import NotificationService


class ImageWorkflowService:
    def __init__(self, notification_service: NotificationService) -> None:
        self.notification_service = notification_service

    async def create_request(
        self,
        db: Session,
        requester_wallet: str,
        payload: ImageWorkflowCreateRequest,
    ) -> ImageWorkflowResponse:
        record = ImageWorkflowRecord(
            requester_wallet=requester_wallet,
            publisher_wallet=payload.publisher_wallet,
            target_wallet=payload.target_wallet,
            provider_name=payload.provider_name,
            requested_image_name=payload.requested_image_name,
            source_instance_id=payload.source_instance_id,
            source_image_ref=payload.source_image_ref,
            status="pending",
            metadata_json=payload.metadata,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            payload.publisher_wallet,
            "image_copy_requested",
            {
                "workflow_id": record.id,
                "requester_wallet": requester_wallet,
                "target_wallet": payload.target_wallet,
                "requested_image_name": payload.requested_image_name,
            },
        )
        return self._to_workflow_schema(record)

    async def confirm_request(
        self,
        db: Session,
        workflow_id: str,
        publisher_wallet: str,
        payload: ImageWorkflowConfirmRequest,
    ) -> ImageWorkflowResponse:
        record = self.get_request(db, workflow_id)
        if record.publisher_wallet != publisher_wallet:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有发布者可以确认镜像复制请求",
            )
        record.note = payload.note
        if payload.approved:
            image_ref = payload.created_image_ref or f"demo-image-ref-{uuid4().hex[:8]}"
            user_image = UserImageRecord(
                owner_wallet=record.target_wallet,
                provider_name=record.provider_name,
                image_ref=image_ref,
                image_name=record.requested_image_name,
                source_workflow_id=record.id,
                source_instance_id=record.source_instance_id,
                source_image_ref=record.source_image_ref,
                status="available",
                metadata_json={"created_by": "image_workflow_confirm"},
            )
            db.add(user_image)
            db.flush()
            record.status = "completed"
            record.created_image_id = user_image.id
            await self.notification_service.publish(
                db,
                record.target_wallet,
                "image_copy_completed",
                {
                    "workflow_id": record.id,
                    "user_image_id": user_image.id,
                    "image_ref": image_ref,
                },
            )
        else:
            record.status = "rejected"
            await self.notification_service.publish(
                db,
                record.requester_wallet,
                "image_copy_rejected",
                {"workflow_id": record.id, "note": payload.note},
            )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_workflow_schema(record)

    def get_request(self, db: Session, workflow_id: str) -> ImageWorkflowRecord:
        stmt = select(ImageWorkflowRecord).where(ImageWorkflowRecord.id == workflow_id)
        record = db.scalar(stmt)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到镜像协作请求: {workflow_id}")
        return record

    def list_user_images(self, db: Session, owner_wallet: str) -> list[UserImageResponse]:
        stmt = (
            select(UserImageRecord)
            .where(UserImageRecord.owner_wallet == owner_wallet)
            .order_by(UserImageRecord.created_at.desc())
        )
        return [self._to_user_image_schema(record) for record in db.scalars(stmt).all()]

    def get_user_image(self, db: Session, image_id: str) -> UserImageRecord:
        stmt = select(UserImageRecord).where(UserImageRecord.id == image_id)
        record = db.scalar(stmt)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到用户镜像: {image_id}")
        return record

    @staticmethod
    def ensure_owner(record: UserImageRecord, wallet_address: str) -> None:
        if record.owner_wallet != wallet_address:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前钱包不是该镜像所有者")

    @staticmethod
    def _to_workflow_schema(record: ImageWorkflowRecord) -> ImageWorkflowResponse:
        return ImageWorkflowResponse(
            id=record.id,
            requester_wallet=record.requester_wallet,
            publisher_wallet=record.publisher_wallet,
            target_wallet=record.target_wallet,
            provider_name=record.provider_name,
            requested_image_name=record.requested_image_name,
            source_instance_id=record.source_instance_id,
            source_image_ref=record.source_image_ref,
            status=record.status,
            created_image_id=record.created_image_id,
            note=record.note,
            metadata=record.metadata_json,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_user_image_schema(record: UserImageRecord) -> UserImageResponse:
        return UserImageResponse(
            id=record.id,
            owner_wallet=record.owner_wallet,
            provider_name=record.provider_name,
            image_ref=record.image_ref,
            image_name=record.image_name,
            source_workflow_id=record.source_workflow_id,
            source_instance_id=record.source_instance_id,
            source_image_ref=record.source_image_ref,
            status=record.status,
            metadata=record.metadata_json,
            created_at=record.created_at,
        )
