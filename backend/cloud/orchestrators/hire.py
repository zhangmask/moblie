from __future__ import annotations

from backend.cloud.contracts.image import ImageSharingPort
from backend.cloud.contracts.instance import InstanceInfo, InstanceLifecyclePort, InstanceSpec
from backend.cloud.registry import ProviderRegistry


class HireOrchestrator:
    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    async def provision_instance(
        self,
        provider_name: str,
        spec: InstanceSpec,
        target_ref: str | None = None,
    ) -> InstanceInfo:
        provider = self.registry.require_capability(provider_name, InstanceLifecyclePort)

        if target_ref and isinstance(provider, ImageSharingPort):
            await provider.share_image(spec.image_ref, target_ref)
            try:
                return await provider.create_instance(spec)
            finally:
                await provider.revoke_shared_image(spec.image_ref, target_ref)

        return await provider.create_instance(spec)
