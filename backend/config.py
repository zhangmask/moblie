from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_STORAGE_ROOT = BASE_DIR / ".data"
DEFAULT_DATABASE_PATH = DEFAULT_STORAGE_ROOT / "agent_os.db"


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_prefix: str
    storage_root: Path
    database_url: str
    solana_rpc_url: str
    solana_program_id: str
    default_provider_name: str
    provider_options: dict[str, dict[str, Any]]

    def get_provider_options(self, provider_name: str) -> dict[str, Any]:
        return dict(self.provider_options.get(provider_name, {}))


def _parse_provider_options() -> dict[str, dict[str, Any]]:
    raw = os.getenv("AGENT_OS_PROVIDER_OPTIONS", "{}").strip() or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    storage_root = Path(os.getenv("AGENT_OS_STORAGE_ROOT", DEFAULT_STORAGE_ROOT)).resolve()
    database_url = os.getenv(
        "AGENT_OS_DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH.resolve().as_posix()}",
    )
    return Settings(
        app_name=os.getenv("AGENT_OS_APP_NAME", "Agent OS MVP Backend"),
        api_prefix=os.getenv("AGENT_OS_API_PREFIX", "/api"),
        storage_root=storage_root,
        database_url=database_url,
        solana_rpc_url=os.getenv("SOLANA_RPC_URL", "http://127.0.0.1:8899"),
        solana_program_id=os.getenv("OMNICLAW_PROGRAM_ID", "localnet-omniclaw"),
        default_provider_name=os.getenv("AGENT_OS_DEFAULT_PROVIDER", "demo"),
        provider_options=_parse_provider_options(),
    )
