from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.database import PaymentOrderRecord, SettlementRecord
from backend.models.schemas import (
    PaymentOrderConfirmRequest,
    PaymentOrderCreateRequest,
    PaymentOrderFreezeRequest,
    PaymentOrderResponse,
    PaymentOrderSettleRequest,
    SettlementResponse,
)
from backend.services.notification_service import NotificationService


class PaymentService:
    def __init__(self, notification_service: NotificationService) -> None:
        self.notification_service = notification_service

    async def create_order(
        self,
        db: Session,
        owner_wallet: str,
        payload: PaymentOrderCreateRequest,
    ) -> PaymentOrderResponse:
        record = PaymentOrderRecord(
            owner_wallet=owner_wallet,
            agent_wallet=payload.agent_wallet,
            agent_os_id=payload.agent_os_id,
            job_pubkey=payload.job_pubkey,
            payment_type=payload.payment_type,
            amount=payload.amount,
            currency=payload.currency,
            chain_name=payload.chain_name,
            status="pending",
            metadata_json=payload.metadata,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            payload.agent_wallet,
            "payment_order_created",
            {"order_id": record.id, "owner_wallet": owner_wallet, "amount": payload.amount},
        )
        return self._to_schema(record)

    async def freeze_order(
        self,
        db: Session,
        order_id: str,
        payload: PaymentOrderFreezeRequest,
    ) -> PaymentOrderResponse:
        record = self.get_order(db, order_id)
        if record.status not in {"pending", "confirmed"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前订单状态不允许冻结")
        record.status = "frozen"
        record.frozen_amount = payload.frozen_amount or record.amount
        metadata = dict(record.metadata_json)
        if payload.note:
            metadata["freeze_note"] = payload.note
        record.metadata_json = metadata
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            record.owner_wallet,
            "payment_frozen",
            {"order_id": record.id, "frozen_amount": record.frozen_amount},
        )
        return self._to_schema(record)

    async def confirm_order(
        self,
        db: Session,
        order_id: str,
        owner_wallet: str,
        payload: PaymentOrderConfirmRequest,
    ) -> PaymentOrderResponse:
        record = self.get_order(db, order_id)
        if record.owner_wallet != owner_wallet:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有付款人可以确认支付订单")
        record.status = "confirmed"
        record.transaction_signature = payload.transaction_signature
        metadata = dict(record.metadata_json)
        if payload.note:
            metadata["note"] = payload.note
        record.metadata_json = metadata
        db.add(record)
        db.commit()
        db.refresh(record)
        await self.notification_service.publish(
            db,
            record.agent_wallet,
            "payment_confirmed",
            {
                "order_id": record.id,
                "owner_wallet": record.owner_wallet,
                "transaction_signature": payload.transaction_signature,
            },
        )
        return self._to_schema(record)

    async def settle_order(
        self,
        db: Session,
        order_id: str,
        payload: PaymentOrderSettleRequest,
    ) -> tuple[PaymentOrderResponse, SettlementResponse]:
        record = self.get_order(db, order_id)
        if record.status not in {"confirmed", "frozen"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前订单状态不允许结算")
        record.status = "settled"
        record.instance_id = payload.instance_id or record.instance_id
        record.settled_amount = payload.settled_amount or record.frozen_amount or record.amount
        metadata = dict(record.metadata_json)
        if payload.note:
            metadata["settle_note"] = payload.note
        record.metadata_json = metadata
        settlement = SettlementRecord(
            order_id=record.id,
            instance_id=record.instance_id,
            owner_wallet=record.owner_wallet,
            publisher_wallet=record.agent_wallet,
            platform_fee=payload.platform_fee,
            publisher_amount=payload.publisher_amount or record.settled_amount or "0",
            refunded_amount=payload.refunded_amount,
            status="settled",
            metadata_json={"payment_type": record.payment_type, **metadata},
        )
        db.add(record)
        db.add(settlement)
        db.commit()
        db.refresh(record)
        db.refresh(settlement)
        await self.notification_service.publish(
            db,
            record.agent_wallet,
            "payment_settled",
            {
                "order_id": record.id,
                "instance_id": record.instance_id,
                "publisher_amount": settlement.publisher_amount,
                "platform_fee": settlement.platform_fee,
            },
        )
        return self._to_schema(record), self._to_settlement_schema(settlement)

    async def bind_instance(
        self,
        db: Session,
        order_id: str,
        instance_id: str,
    ) -> PaymentOrderResponse:
        record = self.get_order(db, order_id)
        record.instance_id = instance_id
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_schema(record)

    def get_order_by_instance(self, db: Session, instance_id: str) -> PaymentOrderRecord | None:
        stmt = select(PaymentOrderRecord).where(PaymentOrderRecord.instance_id == instance_id)
        return db.scalar(stmt)

    def list_settlements_for_publisher(self, db: Session, publisher_wallet: str) -> list[SettlementResponse]:
        stmt = (
            select(SettlementRecord)
            .where(SettlementRecord.publisher_wallet == publisher_wallet)
            .order_by(SettlementRecord.created_at.desc())
        )
        return [self._to_settlement_schema(item) for item in db.scalars(stmt).all()]

    def get_order(self, db: Session, order_id: str) -> PaymentOrderRecord:
        stmt = select(PaymentOrderRecord).where(PaymentOrderRecord.id == order_id)
        record = db.scalar(stmt)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到支付订单: {order_id}")
        return record

    @staticmethod
    def _to_schema(record: PaymentOrderRecord) -> PaymentOrderResponse:
        return PaymentOrderResponse(
            id=record.id,
            owner_wallet=record.owner_wallet,
            agent_wallet=record.agent_wallet,
            agent_os_id=record.agent_os_id,
            instance_id=record.instance_id,
            job_pubkey=record.job_pubkey,
            payment_type=record.payment_type,
            amount=record.amount,
            frozen_amount=record.frozen_amount,
            settled_amount=record.settled_amount,
            currency=record.currency,
            chain_name=record.chain_name,
            status=record.status,
            transaction_signature=record.transaction_signature,
            metadata=record.metadata_json,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_settlement_schema(record: SettlementRecord) -> SettlementResponse:
        return SettlementResponse(
            id=record.id,
            order_id=record.order_id,
            instance_id=record.instance_id,
            owner_wallet=record.owner_wallet,
            publisher_wallet=record.publisher_wallet,
            platform_fee=record.platform_fee,
            publisher_amount=record.publisher_amount,
            refunded_amount=record.refunded_amount,
            status=record.status,
            metadata=record.metadata_json,
            created_at=record.created_at,
        )

    @staticmethod
    def split_amount(total: str, platform_fee_ratio: str = "0.1") -> tuple[str, str]:
        total_decimal = Decimal(total)
        fee = (total_decimal * Decimal(platform_fee_ratio)).quantize(Decimal("0.0001"))
        publisher_amount = total_decimal - fee
        return str(fee), str(publisher_amount)
