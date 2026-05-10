from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_payment_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import (
    PaymentOrderConfirmRequest,
    PaymentOrderCreateRequest,
    PaymentOrderFreezeRequest,
    PaymentOrderResponse,
    PaymentOrderSettleRequest,
    SettlementResponse,
)
from backend.services.payment_service import PaymentService


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/orders", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    payload: PaymentOrderCreateRequest,
    db: Session = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> PaymentOrderResponse:
    return await service.create_order(db, identity.wallet_address, payload)


@router.post("/orders/{order_id}/confirm", response_model=PaymentOrderResponse)
async def confirm_payment_order(
    order_id: str,
    payload: PaymentOrderConfirmRequest,
    db: Session = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> PaymentOrderResponse:
    return await service.confirm_order(db, order_id, identity.wallet_address, payload)


@router.post("/orders/{order_id}/freeze", response_model=PaymentOrderResponse)
async def freeze_payment_order(
    order_id: str,
    payload: PaymentOrderFreezeRequest,
    db: Session = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> PaymentOrderResponse:
    record = service.get_order(db, order_id)
    if record.agent_wallet != identity.wallet_address:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有发布者可以冻结订单")
    return await service.freeze_order(db, order_id, payload)


@router.post("/orders/{order_id}/settle", response_model=SettlementResponse)
async def settle_payment_order(
    order_id: str,
    payload: PaymentOrderSettleRequest,
    db: Session = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> SettlementResponse:
    record = service.get_order(db, order_id)
    if record.agent_wallet != identity.wallet_address:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有发布者可以发起结算")
    _, settlement = await service.settle_order(db, order_id, payload)
    return settlement


@router.get("/orders/{order_id}", response_model=PaymentOrderResponse)
async def get_payment_order(
    order_id: str,
    db: Session = Depends(get_db),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentOrderResponse:
    return service._to_schema(service.get_order(db, order_id))
