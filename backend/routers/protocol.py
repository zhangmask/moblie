from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_protocol_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import (
    AgentOsResponse,
    FireAgentOsResponse,
    HiredInstanceResponse,
    ProtocolAutoHireRequest,
    ProtocolAutoHireResponse,
    ProtocolHireRequest,
    ProtocolHireResponse,
    ProtocolSendTaskRequest,
    ReviewCreateRequest,
    ReviewResponse,
    ReviewSummaryResponse,
    TaskDispatchResponse,
)
from backend.services.protocol_service import ProtocolService


router = APIRouter(prefix="/protocol", tags=["protocol"])


@router.get("/search-agent-os", response_model=list[AgentOsResponse])
async def search_agent_os(
    query: str | None = Query(default=None),
    category: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    max_price: str | None = Query(default=None),
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
) -> list[AgentOsResponse]:
    return service.search_agent_os(
        db,
        query=query,
        category=category,
        skill=skill,
        min_rating=min_rating,
        max_price=max_price,
    )


@router.post("/hire-agent-os", response_model=ProtocolHireResponse)
async def hire_agent_os(
    payload: ProtocolHireRequest,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ProtocolHireResponse:
    if identity.wallet_address != payload.owner_wallet:
        payload = payload.model_copy(update={"owner_wallet": identity.wallet_address})
    return await service.hire_agent_os(db, payload)


@router.post("/send-task", response_model=TaskDispatchResponse)
async def send_task(
    payload: ProtocolSendTaskRequest,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> TaskDispatchResponse:
    record = service.instance_service.get_instance(db, payload.instance_id)
    service.instance_service.ensure_owner(record, identity.wallet_address)
    return await service.send_task(db, payload)


@router.post("/fire-agent-os/{instance_id}", response_model=FireAgentOsResponse)
async def fire_agent_os(
    instance_id: str,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> FireAgentOsResponse:
    return await service.fire_agent_os(db, instance_id, identity.wallet_address)


@router.get("/list-hired", response_model=list[HiredInstanceResponse])
async def list_hired(
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[HiredInstanceResponse]:
    return service.list_hired(db, identity.wallet_address)


@router.post("/rate-agent-os", response_model=ReviewResponse)
async def rate_agent_os(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ReviewResponse:
    return service.rate_agent_os(db, identity.wallet_address, payload)


@router.post("/rate-publisher", response_model=ReviewResponse)
async def rate_publisher(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ReviewResponse:
    return service.rate_publisher(db, identity.wallet_address, payload)


@router.get("/reviews/{target_type}/{target_id}", response_model=ReviewSummaryResponse)
async def get_reviews(
    target_type: str,
    target_id: str,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
) -> ReviewSummaryResponse:
    return service.get_reviews(db, target_type, target_id)


@router.post("/auto-hire", response_model=ProtocolAutoHireResponse)
async def auto_hire(
    payload: ProtocolAutoHireRequest,
    db: Session = Depends(get_db),
    service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ProtocolAutoHireResponse:
    if identity.wallet_address != payload.owner_wallet:
        payload = payload.model_copy(update={"owner_wallet": identity.wallet_address})
    return await service.auto_hire(db, payload)
