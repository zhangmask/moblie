from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_agent_service, get_db
from backend.models.schemas import AgentSummary
from backend.services.agent_service import AgentService


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
async def list_agents(
    q: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    publisher_wallet: str | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    sort_by: str = Query(default="reputation"),
    db: Session = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
) -> list[AgentSummary]:
    return await agent_service.list_agents(
        db=db,
        query=q,
        skill=skill,
        publisher_wallet=publisher_wallet,
        min_rating=min_rating,
        sort_by=sort_by,
    )


@router.get("/{agent_pubkey}", response_model=AgentSummary)
async def get_agent(
    agent_pubkey: str,
    db: Session = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentSummary:
    return await agent_service.get_agent(db, agent_pubkey)
