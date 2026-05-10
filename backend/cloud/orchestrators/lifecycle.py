from __future__ import annotations

from backend.cloud.contracts.instance import InstanceInfo, InstanceLifecyclePort
from backend.cloud.registry import ProviderRegistry


class InstanceLifecycleOrchestrator:
    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    async def destroy_instance(self, provider_name: str, instance_id: str) -> bool:
        provider = self.registry.require_capability(provider_name, InstanceLifecyclePort)
        return await provider.destroy_instance(instance_id)

    async def get_instance_status(self, provider_name: str, instance_id: str) -> InstanceInfo:
        provider = self.registry.require_capability(provider_name, InstanceLifecyclePort)
        return await provider.get_instance_status(instance_id)
