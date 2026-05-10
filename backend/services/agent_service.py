from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.schemas import AgentSummary
from backend.services.review_service import ReviewService
from backend.services.solana_service import SolanaService


class AgentService:
    def __init__(self, solana_service: SolanaService, review_service: ReviewService) -> None:
        self.solana_service = solana_service
        self.review_service = review_service

    async def list_agents(
        self,
        db: Session,
        query: str | None = None,
        skill: str | None = None,
        publisher_wallet: str | None = None,
        min_rating: float | None = None,
        sort_by: str = "reputation",
    ) -> list[AgentSummary]:
        agents = await self.solana_service.list_agents()
        review_map = self.review_service.get_summary_map(
            db,
            "agent_os",
            [agent.agent_account for agent in agents],
        )
        publisher_map = self.review_service.get_summary_map(
            db,
            "publisher",
            [agent.owner_wallet for agent in agents],
        )
        enriched: list[AgentSummary] = []
        for agent in agents:
            agent_summary = review_map.get(agent.agent_account)
            publisher_summary = publisher_map.get(agent.owner_wallet)
            enriched.append(
                agent.model_copy(
                    update={
                        "average_rating": agent_summary.average_rating if agent_summary else 0.0,
                        "review_count": agent_summary.review_count if agent_summary else 0,
                        "publisher_average_rating": publisher_summary.average_rating if publisher_summary else 0.0,
                        "publisher_review_count": publisher_summary.review_count if publisher_summary else 0,
                    }
                )
            )
        if query:
            lowered = query.lower()
            enriched = [
                agent
                for agent in enriched
                if lowered in agent.name.lower() or lowered in agent.skill.lower() or lowered in agent.agent_account.lower()
            ]
        if skill:
            lowered_skill = skill.lower()
            enriched = [agent for agent in enriched if lowered_skill in agent.skill.lower()]
        if publisher_wallet:
            enriched = [agent for agent in enriched if agent.owner_wallet == publisher_wallet]
        if min_rating is not None:
            enriched = [agent for agent in enriched if agent.average_rating >= min_rating]

        sort_key_map = {
            "rating": lambda item: (item.average_rating, item.review_count, item.reputation),
            "jobs": lambda item: (item.completed_jobs, item.reputation),
            "publisher_rating": lambda item: (item.publisher_average_rating, item.publisher_review_count),
            "reputation": lambda item: (item.reputation, item.completed_jobs),
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["reputation"])
        return sorted(enriched, key=key_fn, reverse=True)

    async def get_agent(self, db: Session, agent_pubkey: str):
        try:
            agent = await self.solana_service.get_agent(agent_pubkey)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到 Agent: {agent_pubkey}",
            ) from exc
        review_summary = self.review_service.get_summary(db, "agent_os", agent.agent_account)
        publisher_summary = self.review_service.get_summary(db, "publisher", agent.owner_wallet)
        return agent.model_copy(
            update={
                "average_rating": review_summary.average_rating,
                "review_count": review_summary.review_count,
                "publisher_average_rating": publisher_summary.average_rating,
                "publisher_review_count": publisher_summary.review_count,
            }
        )
