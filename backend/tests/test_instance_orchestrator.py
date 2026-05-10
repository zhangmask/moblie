from __future__ import annotations

import asyncio

from backend.cloud.contracts.instance import InstanceSpec
from backend.cloud.demo_provider import DemoCloudProvider
from backend.cloud.orchestrators.hire import HireOrchestrator
from backend.cloud.orchestrators.lifecycle import InstanceLifecycleOrchestrator
from backend.cloud.registry import ProviderRegistry


def test_hire_orchestrator_uses_registry() -> None:
    async def run_test():
        registry = ProviderRegistry()
        registry.register("demo", DemoCloudProvider())
        orchestrator = HireOrchestrator(registry)
        return await orchestrator.provision_instance(
            provider_name="demo",
            spec=InstanceSpec(
                image_ref="img-demo",
                instance_type="standard.small",
                network_ref="network-a",
                security_groups=["default"],
            ),
            target_ref="platform-demo-account",
        )

    result = asyncio.run(run_test())
    assert result.provider_name == "demo"
    assert result.instance_id.startswith("demo-")


def test_lifecycle_orchestrator_reads_status() -> None:
    async def run_test():
        registry = ProviderRegistry()
        registry.register("demo", DemoCloudProvider())
        orchestrator = InstanceLifecycleOrchestrator(registry)
        return await orchestrator.get_instance_status("demo", "demo-1234")

    status = asyncio.run(run_test())
    assert status.instance_id == "demo-1234"
    assert status.status == "running"
