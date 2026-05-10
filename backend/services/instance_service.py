from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.cloud.contracts.instance import InstanceSpec
from backend.cloud.orchestrators.hire import HireOrchestrator
from backend.cloud.orchestrators.lifecycle import InstanceLifecycleOrchestrator
from backend.config import Settings
from backend.models.database import InstanceRecord
from backend.models.schemas import (
    HiredInstanceResponse,
    InstanceCreateRequest,
    InstanceResponse,
    TaskDispatchRequest,
    TaskDispatchResponse,
)
from backend.services.review_service import ReviewService
from backend.services.notification_service import NotificationService


class InstanceService:
    def __init__(
        self,
        settings: Settings,
        notification_service: NotificationService,
        hire_orchestrator: HireOrchestrator,
        lifecycle_orchestrator: InstanceLifecycleOrchestrator,
        review_service: ReviewService,
    ) -> None:
        self.settings = settings
        self.notification_service = notification_service
        self.hire_orchestrator = hire_orchestrator
        self.lifecycle_orchestrator = lifecycle_orchestrator
        self.review_service = review_service

    async def create_instance(self, db: Session, payload: InstanceCreateRequest) -> InstanceResponse:
        provider_name = payload.provider_name or self.settings.default_provider_name
        provider_options = self.settings.get_provider_options(provider_name)
        provider_options.update(payload.provider_config)
        instance_info = await self.hire_orchestrator.provision_instance(
            provider_name=provider_name,
            spec=InstanceSpec(
                image_ref=payload.image_ref,
                instance_type=payload.instance_type,
                network_ref=payload.network_ref,
                security_groups=payload.security_groups,
                user_data=payload.user_data,
                metadata={"job_pubkey": payload.job_pubkey, "owner_wallet": payload.owner_wallet},
            ),
            target_ref=provider_options.get("target_ref"),
        )
        record = InstanceRecord(
            job_pubkey=payload.job_pubkey,
            provider_name=provider_name,
            provider_instance_id=instance_info.instance_id,
            image_ref=payload.image_ref,
            status=instance_info.status,
            public_ip=instance_info.public_ip,
            private_ip=instance_info.private_ip,
            owner_wallet=payload.owner_wallet,
            agent_wallet=payload.agent_wallet,
            agent_os_id=payload.agent_os_id,
            instance_type=payload.instance_type,
            network_ref=payload.network_ref,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            payload.owner_wallet,
            "instance_ready",
            {
                "instance_id": record.id,
                "provider_instance_id": record.provider_instance_id,
                "job_pubkey": payload.job_pubkey,
            },
        )
        return self._to_schema(record)

    def get_instance(self, db: Session, instance_id: str) -> InstanceRecord:
        stmt = select(InstanceRecord).where(InstanceRecord.id == instance_id)
        record = db.scalar(stmt)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到实例: {instance_id}",
            )
        return record

    async def destroy_instance(self, db: Session, instance_id: str) -> InstanceResponse:
        record = self.get_instance(db, instance_id)
        if record.provider_instance_id:
            await self.lifecycle_orchestrator.destroy_instance(
                record.provider_name,
                record.provider_instance_id,
            )
        record.status = "destroyed"
        record.destroyed_at = datetime.now(timezone.utc)
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            record.owner_wallet,
            "instance_destroyed",
            {"instance_id": record.id, "provider_instance_id": record.provider_instance_id},
        )
        return self._to_schema(record)

    async def dispatch_task(
        self,
        db: Session,
        instance_id: str,
        payload: TaskDispatchRequest,
    ) -> TaskDispatchResponse:
        record = self.get_instance(db, instance_id)
        await self.notification_service.publish(
            db,
            record.agent_wallet,
            "task_received",
            {
                "instance_id": record.id,
                "task": payload.task,
                "metadata": payload.metadata,
            },
        )
        return TaskDispatchResponse(
            instance_id=record.id,
            accepted=True,
            message="任务已记录，当前由平台通知 Agent 侧处理",
        )

    def list_hired(self, db: Session, owner_wallet: str) -> list[HiredInstanceResponse]:
        stmt = (
            select(InstanceRecord)
            .where(InstanceRecord.owner_wallet == owner_wallet)
            .order_by(InstanceRecord.created_at.desc())
        )
        records = db.scalars(stmt).all()
        results: list[HiredInstanceResponse] = []
        for record in records:
            base = self._to_schema(record)
            results.append(
                HiredInstanceResponse(
                    **base.model_dump(),
                    agent_os_reviewed=self.review_service.has_review(db, "agent_os", record.id, owner_wallet),
                    publisher_reviewed=self.review_service.has_review(db, "publisher", record.id, owner_wallet),
                )
            )
        return results

    @staticmethod
    def ensure_owner(record: InstanceRecord, wallet_address: str) -> None:
        if record.owner_wallet != wallet_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前钱包不是该实例所有者",
            )

    @staticmethod
    def _to_schema(record: InstanceRecord) -> InstanceResponse:
        return InstanceResponse(
            id=record.id,
            job_pubkey=record.job_pubkey,
            provider_name=record.provider_name,
            provider_instance_id=record.provider_instance_id,
            image_ref=record.image_ref,
            agent_os_id=record.agent_os_id,
            status=record.status,
            public_ip=record.public_ip,
            private_ip=record.private_ip,
            owner_wallet=record.owner_wallet,
            agent_wallet=record.agent_wallet,
            instance_type=record.instance_type,
            network_ref=record.network_ref,
            created_at=record.created_at,
            destroyed_at=record.destroyed_at,
        )
