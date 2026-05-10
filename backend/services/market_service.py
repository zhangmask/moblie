from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import AgentOsRecord, ImageWorkflowRecord, PaymentOrderRecord, SettlementRecord
from backend.models.schemas import AgentOsResponse, AgentOsUpsertRequest, PublisherDashboardResponse
from backend.services.review_service import ReviewService


class MarketService:
    def __init__(self, review_service: ReviewService) -> None:
        self.review_service = review_service

    def register_agent_os(
        self,
        db: Session,
        publisher_wallet: str,
        payload: AgentOsUpsertRequest,
    ) -> AgentOsResponse:
        record = AgentOsRecord(
            publisher_wallet=publisher_wallet,
            agent_account=payload.agent_account,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            skill=payload.skill,
            pricing_model=payload.pricing_model,
            price_amount=payload.price_amount,
            currency=payload.currency,
            region=payload.region,
            cpu_cores=payload.cpu_cores,
            memory_gb=payload.memory_gb,
            disk_gb=payload.disk_gb,
            image_ref=payload.image_ref,
            metadata_json=payload.metadata,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_schema(db, record)

    def update_agent_os(
        self,
        db: Session,
        agent_os_id: str,
        publisher_wallet: str,
        payload: AgentOsUpsertRequest,
    ) -> AgentOsResponse:
        record = self.get_agent_os_record(db, agent_os_id)
        self.ensure_publisher(record, publisher_wallet)
        record.agent_account = payload.agent_account
        record.name = payload.name
        record.description = payload.description
        record.category = payload.category
        record.skill = payload.skill
        record.pricing_model = payload.pricing_model
        record.price_amount = payload.price_amount
        record.currency = payload.currency
        record.region = payload.region
        record.cpu_cores = payload.cpu_cores
        record.memory_gb = payload.memory_gb
        record.disk_gb = payload.disk_gb
        record.image_ref = payload.image_ref
        record.metadata_json = payload.metadata
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_schema(db, record)

    def list_market(
        self,
        db: Session,
        q: str | None = None,
        category: str | None = None,
        skill: str | None = None,
        publisher_wallet: str | None = None,
        min_rating: float | None = None,
        max_price: str | None = None,
        sort_by: str = "rating",
    ) -> list[AgentOsResponse]:
        stmt = select(AgentOsRecord).where(AgentOsRecord.status == "published")
        records = list(db.scalars(stmt).all())
        enriched = [self._to_schema(db, record) for record in records]
        if q:
            lowered = q.lower()
            enriched = [
                item
                for item in enriched
                if lowered in item.name.lower()
                or lowered in item.description.lower()
                or lowered in item.skill.lower()
            ]
        if category:
            enriched = [item for item in enriched if item.category == category]
        if skill:
            lowered_skill = skill.lower()
            enriched = [item for item in enriched if lowered_skill in item.skill.lower()]
        if publisher_wallet:
            enriched = [item for item in enriched if item.publisher_wallet == publisher_wallet]
        if min_rating is not None:
            enriched = [item for item in enriched if item.average_rating >= min_rating]
        if max_price is not None:
            try:
                limit = Decimal(max_price)
                enriched = [item for item in enriched if Decimal(item.price_amount) <= limit]
            except InvalidOperation:
                pass
        sort_key_map = {
            "price": lambda item: Decimal(item.price_amount),
            "rating": lambda item: (item.average_rating, item.review_count),
            "reviews": lambda item: (item.review_count, item.average_rating),
            "newest": lambda item: item.created_at.timestamp(),
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["rating"])
        return sorted(enriched, key=key_fn, reverse=sort_by != "price")

    def list_my_agent_os(self, db: Session, publisher_wallet: str) -> list[AgentOsResponse]:
        stmt = (
            select(AgentOsRecord)
            .where(AgentOsRecord.publisher_wallet == publisher_wallet)
            .order_by(AgentOsRecord.created_at.desc())
        )
        return [self._to_schema(db, record) for record in db.scalars(stmt).all()]

    def get_agent_os(self, db: Session, agent_os_id: str) -> AgentOsResponse:
        return self._to_schema(db, self.get_agent_os_record(db, agent_os_id))

    def get_agent_os_record(self, db: Session, agent_os_id: str) -> AgentOsRecord:
        stmt = select(AgentOsRecord).where(AgentOsRecord.id == agent_os_id)
        record = db.scalar(stmt)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到 Agent OS: {agent_os_id}")
        return record

    def get_publisher_dashboard(self, db: Session, publisher_wallet: str) -> PublisherDashboardResponse:
        agent_os_records = self.list_my_agent_os(db, publisher_wallet)
        pending_requests = len(
            list(
                db.scalars(
                    select(ImageWorkflowRecord).where(
                        ImageWorkflowRecord.publisher_wallet == publisher_wallet,
                        ImageWorkflowRecord.status == "pending",
                    )
                ).all()
            )
        )
        order_ids = [record.id for record in db.scalars(select(PaymentOrderRecord)).all() if record.agent_wallet == publisher_wallet]
        settlements = list(
            db.scalars(select(SettlementRecord).where(SettlementRecord.publisher_wallet == publisher_wallet)).all()
        )
        total_revenue = sum(Decimal(item.publisher_amount) for item in settlements) if settlements else Decimal("0")
        frozen_orders = len(
            [record for record in db.scalars(select(PaymentOrderRecord).where(PaymentOrderRecord.agent_wallet == publisher_wallet)).all() if record.status == "frozen"]
        )
        settled_orders = len(
            [record for record in db.scalars(select(PaymentOrderRecord).where(PaymentOrderRecord.agent_wallet == publisher_wallet)).all() if record.status == "settled"]
        )
        return PublisherDashboardResponse(
            publisher_wallet=publisher_wallet,
            total_agent_os=len(agent_os_records),
            published_agent_os=len([item for item in agent_os_records if item.status == "published"]),
            pending_image_requests=pending_requests,
            total_orders=len(order_ids),
            frozen_orders=frozen_orders,
            settled_orders=settled_orders,
            total_revenue=str(total_revenue),
            recent_agent_os=agent_os_records[:5],
        )

    @staticmethod
    def ensure_publisher(record: AgentOsRecord, publisher_wallet: str) -> None:
        if record.publisher_wallet != publisher_wallet:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前钱包不是该 Agent OS 发布者")

    def _to_schema(self, db: Session, record: AgentOsRecord) -> AgentOsResponse:
        review_summary = self.review_service.get_summary(db, "agent_os", record.id)
        publisher_summary = self.review_service.get_summary(db, "publisher", record.publisher_wallet)
        return AgentOsResponse(
            id=record.id,
            publisher_wallet=record.publisher_wallet,
            agent_account=record.agent_account,
            name=record.name,
            description=record.description,
            category=record.category,
            skill=record.skill,
            pricing_model=record.pricing_model,
            price_amount=record.price_amount,
            currency=record.currency,
            region=record.region,
            cpu_cores=record.cpu_cores,
            memory_gb=record.memory_gb,
            disk_gb=record.disk_gb,
            image_ref=record.image_ref,
            status=record.status,
            metadata=record.metadata_json,
            average_rating=review_summary.average_rating,
            review_count=review_summary.review_count,
            publisher_average_rating=publisher_summary.average_rating,
            publisher_review_count=publisher_summary.review_count,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
