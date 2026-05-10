from __future__ import annotations

import asyncio
from pathlib import Path

from backend.cloud.demo_provider import DemoCloudProvider
from backend.cloud.orchestrators.file_exchange import FileExchangeOrchestrator
from backend.cloud.registry import ProviderRegistry


def test_upload_file_uses_registry_provider(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("hello", encoding="utf-8")

    async def run_test():
        registry = ProviderRegistry()
        registry.register("demo", DemoCloudProvider())
        orchestrator = FileExchangeOrchestrator(registry)
        return await orchestrator.upload_file("demo", "ins-1", str(source), "/remote/input.txt")

    result = asyncio.run(run_test())
    assert result.path == str(source)
    assert result.size_bytes == len("hello".encode("utf-8"))


def test_download_file_creates_local_artifact(tmp_path: Path) -> None:
    async def run_test():
        registry = ProviderRegistry()
        registry.register("demo", DemoCloudProvider())
        orchestrator = FileExchangeOrchestrator(registry)
        target = tmp_path / "output.txt"
        return await orchestrator.download_file("demo", "ins-1", "/output/output.txt", str(target))

    result = asyncio.run(run_test())
    assert Path(result.path).exists()
    assert "demo download" in Path(result.path).read_text(encoding="utf-8")
