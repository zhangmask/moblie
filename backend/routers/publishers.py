from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_market_service, get_payment_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import AgentOsResponse, AgentOsUpsertRequest, PublisherDashboardResponse, SettlementResponse
from backend.services.market_service import MarketService
from backend.services.payment_service import PaymentService


router = APIRouter(prefix="/publishers", tags=["publishers"])


@router.post("/agent-os", response_model=AgentOsResponse, status_code=status.HTTP_201_CREATED)
async def register_agent_os(
    payload: AgentOsUpsertRequest,
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> AgentOsResponse:
    return service.register_agent_os(db, identity.wallet_address, payload)


@router.put("/agent-os/{agent_os_id}", response_model=AgentOsResponse)
async def update_agent_os(
    agent_os_id: str,
    payload: AgentOsUpsertRequest,
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> AgentOsResponse:
    return service.update_agent_os(db, agent_os_id, identity.wallet_address, payload)


@router.get("/agent-os", response_model=list[AgentOsResponse])
async def list_my_agent_os(
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[AgentOsResponse]:
    return service.list_my_agent_os(db, identity.wallet_address)


@router.get("/dashboard", response_model=PublisherDashboardResponse)
async def get_publisher_dashboard(
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> PublisherDashboardResponse:
    return service.get_publisher_dashboard(db, identity.wallet_address)


@router.get("/settlements", response_model=list[SettlementResponse])
async def list_publisher_settlements(
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[SettlementResponse]:
    return payment_service.list_settlements_for_publisher(db, identity.wallet_address)
