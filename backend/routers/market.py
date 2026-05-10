from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_market_service
from backend.models.schemas import AgentOsResponse
from backend.services.market_service import MarketService


router = APIRouter(prefix="/market", tags=["market"])


@router.get("/agent-os", response_model=list[AgentOsResponse])
async def list_market_agent_os(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    publisher_wallet: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    max_price: str | None = Query(default=None),
    sort_by: str = Query(default="rating"),
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> list[AgentOsResponse]:
    return service.list_market(
        db,
        q=q,
        category=category,
        skill=skill,
        publisher_wallet=publisher_wallet,
        min_rating=min_rating,
        max_price=max_price,
        sort_by=sort_by,
    )


@router.get("/agent-os/{agent_os_id}", response_model=AgentOsResponse)
async def get_market_agent_os(
    agent_os_id: str,
    db: Session = Depends(get_db),
    service: MarketService = Depends(get_market_service),
) -> AgentOsResponse:
    return service.get_agent_os(db, agent_os_id)
