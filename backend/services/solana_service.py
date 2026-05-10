from __future__ import annotations

import json
from pathlib import Path

from backend.config import Settings
from backend.models.schemas import AgentSummary


class SolanaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.project_root = Path(__file__).resolve().parents[2]

    async def list_agents(self) -> list[AgentSummary]:
        program_id = self._load_program_id()
        return [
            AgentSummary(
                agent_account="demo-agent-account",
                owner_wallet="demo-agent-owner",
                name="ClawGPT",
                skill="Solana + Agent OS Demo",
                reputation=100,
                completed_jobs=0,
                source=f"omniclaw:{program_id}",
            )
        ]

    async def get_agent(self, agent_pubkey: str) -> AgentSummary:
        for agent in await self.list_agents():
            if agent.agent_account == agent_pubkey or agent.owner_wallet == agent_pubkey:
                return agent
        raise KeyError(agent_pubkey)

    def _load_program_id(self) -> str:
        idl_path = self.project_root / "target" / "idl" / "omniclaw.json"
        if idl_path.exists():
            with idl_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return str(data.get("address") or self.settings.solana_program_id)
        return self.settings.solana_program_id
