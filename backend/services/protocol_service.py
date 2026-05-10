from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.schemas import (
    FireAgentOsResponse,
    HiredInstanceResponse,
    InstanceCreateRequest,
    PaymentOrderConfirmRequest,
    PaymentOrderCreateRequest,
    ProtocolAutoHireResponse,
    PaymentOrderSettleRequest,
    ProtocolHireResponse,
    ProtocolAutoHireRequest,
    ProtocolHireRequest,
    ProtocolSendTaskRequest,
    ReviewCreateRequest,
    ReviewSummaryResponse,
)
from backend.services.instance_service import InstanceService
from backend.services.market_service import MarketService
from backend.services.payment_service import PaymentService
from backend.services.review_service import ReviewService


class ProtocolService:
    def __init__(
        self,
        market_service: MarketService,
        instance_service: InstanceService,
        payment_service: PaymentService,
        review_service: ReviewService,
    ) -> None:
        self.market_service = market_service
        self.instance_service = instance_service
        self.payment_service = payment_service
        self.review_service = review_service

    def search_agent_os(
        self,
        db: Session,
        query: str | None = None,
        category: str | None = None,
        skill: str | None = None,
        min_rating: float | None = None,
        max_price: str | None = None,
    ):
        return self.market_service.list_market(
            db,
            q=query,
            category=category,
            skill=skill,
            min_rating=min_rating,
            max_price=max_price,
        )

    async def hire_agent_os(self, db: Session, payload: ProtocolHireRequest):
        agent_os = self.market_service.get_agent_os(db, payload.agent_os_id)
        if not agent_os.image_ref:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该 Agent OS 还未登记可用镜像")
        order = await self.payment_service.create_order(
            db,
            payload.owner_wallet,
            PaymentOrderCreateRequest(
                agent_wallet=agent_os.publisher_wallet,
                agent_os_id=agent_os.id,
                job_pubkey=payload.job_pubkey,
                payment_type="hire_agent_os",
                amount=agent_os.price_amount,
                currency=agent_os.currency,
                metadata={"payment_method": payload.payment_method},
            ),
        )
        order = await self.payment_service.freeze_order(db, order.id, frozen_amount_request(agent_os.price_amount))
        order = await self.payment_service.confirm_order(
            db,
            order.id,
            payload.owner_wallet,
            PaymentOrderConfirmRequest(
                transaction_signature=f"demo-hire-{order.id}",
                note="hackathon-mvp-auto-confirm",
            ),
        )
        instance = await self.instance_service.create_instance(
            db,
            InstanceCreateRequest(
                job_pubkey=payload.job_pubkey,
                provider_name="demo",
                image_ref=agent_os.image_ref,
                owner_wallet=payload.owner_wallet,
                agent_wallet=agent_os.publisher_wallet,
                agent_os_id=agent_os.id,
                instance_type=payload.instance_type,
                network_ref=payload.network_ref,
                security_groups=payload.security_groups,
                user_data=payload.user_data,
            ),
        )
        payment = await self.payment_service.bind_instance(db, order.id, instance.id)
        return ProtocolHireResponse(instance=instance, payment=payment, agent_os=agent_os)

    async def send_task(self, db: Session, payload: ProtocolSendTaskRequest):
        return await self.instance_service.dispatch_task(
            db,
            payload.instance_id,
            task_dispatch_request(payload),
        )

    async def fire_agent_os(self, db: Session, instance_id: str, owner_wallet: str) -> FireAgentOsResponse:
        record = self.instance_service.get_instance(db, instance_id)
        self.instance_service.ensure_owner(record, owner_wallet)
        destroyed = await self.instance_service.destroy_instance(db, instance_id)
        hired = HiredInstanceResponse(
            **destroyed.model_dump(),
            agent_os_reviewed=self.review_service.has_review(db, "agent_os", instance_id, owner_wallet),
            publisher_reviewed=self.review_service.has_review(db, "publisher", instance_id, owner_wallet),
        )
        order_record = self.payment_service.get_order_by_instance(db, instance_id)
        if order_record is None:
            return FireAgentOsResponse(
                instance=hired,
                payment=None,
                settlement=None,
                final_cost="0",
                refunded_amount="0",
                message="实例已释放，当前没有关联支付订单",
            )
        platform_fee, publisher_amount = self.payment_service.split_amount(
            order_record.frozen_amount or order_record.amount
        )
        payment, settlement = await self.payment_service.settle_order(
            db,
            order_record.id,
            PaymentOrderSettleRequest(
                instance_id=instance_id,
                settled_amount=order_record.frozen_amount or order_record.amount,
                platform_fee=platform_fee,
                publisher_amount=publisher_amount,
                refunded_amount="0",
                note="fire_agent_os 自动结算",
            ),
        )
        return FireAgentOsResponse(
            instance=hired,
            payment=payment,
            settlement=settlement,
            final_cost=payment.settled_amount or payment.amount,
            refunded_amount=settlement.refunded_amount,
            message="实例已释放并完成结算",
        )

    def list_hired(self, db: Session, owner_wallet: str):
        return self.instance_service.list_hired(db, owner_wallet)

    def rate_agent_os(self, db: Session, owner_wallet: str, payload: ReviewCreateRequest):
        return self.review_service.create_agent_os_review(db, owner_wallet, payload)

    def rate_publisher(self, db: Session, owner_wallet: str, payload: ReviewCreateRequest):
        return self.review_service.create_publisher_review(db, owner_wallet, payload)

    def get_reviews(self, db: Session, target_type: str, target_id: str) -> ReviewSummaryResponse:
        return self.review_service.get_summary(db, target_type, target_id)

    async def auto_hire(self, db: Session, payload: ProtocolAutoHireRequest):
        results = self.search_agent_os(
            db,
            query=payload.query,
            min_rating=payload.min_rating,
            max_price=payload.max_price,
        )
        if not results:
            results = self.search_agent_os(
                db,
                query=None,
                min_rating=payload.min_rating,
                max_price=payload.max_price,
            )
        if not results:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="没有找到符合条件的 Agent OS")
        best = results[0]
        hire_result = await self.hire_agent_os(
            db,
            ProtocolHireRequest(
                agent_os_id=best.id,
                owner_wallet=payload.owner_wallet,
                payment_method="agent_to_agent",
                job_pubkey=f"auto-{payload.requester_agent_id}",
            ),
        )
        task_result = await self.send_task(
            db,
            ProtocolSendTaskRequest(
                instance_id=hire_result.instance.id,
                task=payload.task,
                metadata={
                    "requester_agent_id": payload.requester_agent_id,
                    "auto_hired_agent_os_id": best.id,
                },
            ),
        )
        return ProtocolAutoHireResponse(match=best, hire=hire_result, task=task_result)


def frozen_amount_request(amount: str):
    from backend.models.schemas import PaymentOrderFreezeRequest

    return PaymentOrderFreezeRequest(frozen_amount=amount, note="hire_agent_os 自动冻结")


def task_dispatch_request(payload: ProtocolSendTaskRequest):
    from backend.models.schemas import TaskDispatchRequest

    metadata = dict(payload.metadata)
    if payload.files:
        metadata["files"] = payload.files
    return TaskDispatchRequest(task=payload.task, metadata=metadata)
