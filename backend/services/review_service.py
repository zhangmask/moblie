from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import InstanceRecord, ReviewRecord
from backend.models.schemas import ReviewCreateRequest, ReviewResponse, ReviewSummaryResponse


class ReviewService:
    def create_agent_os_review(
        self,
        db: Session,
        reviewer_wallet: str,
        payload: ReviewCreateRequest,
    ) -> ReviewResponse:
        instance = self._get_owned_instance(db, payload.instance_id, reviewer_wallet)
        target_id = instance.agent_os_id or instance.image_ref
        record = self._create_review(db, "agent_os", target_id, reviewer_wallet, instance.id, payload)
        return self._to_schema(record)

    def create_publisher_review(
        self,
        db: Session,
        reviewer_wallet: str,
        payload: ReviewCreateRequest,
    ) -> ReviewResponse:
        instance = self._get_owned_instance(db, payload.instance_id, reviewer_wallet)
        target_id = instance.agent_wallet
        record = self._create_review(db, "publisher", target_id, reviewer_wallet, instance.id, payload)
        return self._to_schema(record)

    def get_summary(self, db: Session, target_type: str, target_id: str) -> ReviewSummaryResponse:
        stmt = (
            select(ReviewRecord)
            .where(ReviewRecord.target_type == target_type, ReviewRecord.target_id == target_id)
            .order_by(ReviewRecord.created_at.desc())
        )
        records = list(db.scalars(stmt).all())
        if not records:
            return ReviewSummaryResponse(
                target_type=target_type,
                target_id=target_id,
                average_rating=0.0,
                review_count=0,
                dimension_averages={},
                reviews=[],
            )
        dimension_values: dict[str, list[float]] = defaultdict(list)
        for record in records:
            for key, value in record.dimensions_json.items():
                if isinstance(value, (int, float)):
                    dimension_values[key].append(float(value))
        return ReviewSummaryResponse(
            target_type=target_type,
            target_id=target_id,
            average_rating=round(sum(record.rating for record in records) / len(records), 2),
            review_count=len(records),
            dimension_averages={
                key: round(sum(values) / len(values), 2) for key, values in dimension_values.items() if values
            },
            reviews=[self._to_schema(record) for record in records],
        )

    def get_summary_map(
        self,
        db: Session,
        target_type: str,
        target_ids: list[str],
    ) -> dict[str, ReviewSummaryResponse]:
        return {target_id: self.get_summary(db, target_type, target_id) for target_id in target_ids if target_id}

    def has_review(self, db: Session, target_type: str, instance_id: str, reviewer_wallet: str) -> bool:
        stmt = select(ReviewRecord).where(
            ReviewRecord.target_type == target_type,
            ReviewRecord.instance_id == instance_id,
            ReviewRecord.reviewer_wallet == reviewer_wallet,
        )
        return db.scalar(stmt) is not None

    def _create_review(
        self,
        db: Session,
        target_type: str,
        target_id: str,
        reviewer_wallet: str,
        instance_id: str,
        payload: ReviewCreateRequest,
    ) -> ReviewRecord:
        if self.has_review(db, target_type, instance_id, reviewer_wallet):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该实例的此类评价已提交")
        record = ReviewRecord(
            target_type=target_type,
            target_id=target_id,
            instance_id=instance_id,
            reviewer_wallet=reviewer_wallet,
            rating=payload.rating,
            comment=payload.comment,
            dimensions_json=payload.dimensions,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def _get_owned_instance(db: Session, instance_id: str, reviewer_wallet: str) -> InstanceRecord:
        stmt = select(InstanceRecord).where(InstanceRecord.id == instance_id)
        instance = db.scalar(stmt)
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到实例: {instance_id}")
        if instance.owner_wallet != reviewer_wallet:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有实例所有者才能评价")
        return instance

    @staticmethod
    def _to_schema(record: ReviewRecord) -> ReviewResponse:
        return ReviewResponse(
            id=record.id,
            target_type=record.target_type,
            target_id=record.target_id,
            instance_id=record.instance_id,
            reviewer_wallet=record.reviewer_wallet,
            rating=record.rating,
            comment=record.comment,
            dimensions=record.dimensions_json,
            created_at=record.created_at,
        )
