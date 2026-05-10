from __future__ import annotations

from backend.cloud.contracts.file_transfer import FileTransferPort, FileTransferResult
from backend.cloud.registry import ProviderRegistry


class FileExchangeOrchestrator:
    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    async def upload_file(
        self,
        provider_name: str,
        instance_id: str,
        local_path: str,
        remote_path: str,
    ) -> FileTransferResult:
        provider = self.registry.require_capability(provider_name, FileTransferPort)
        return await provider.upload_file(instance_id, local_path, remote_path)

    async def download_file(
        self,
        provider_name: str,
        instance_id: str,
        remote_path: str,
        local_path: str,
    ) -> FileTransferResult:
        provider = self.registry.require_capability(provider_name, FileTransferPort)
        return await provider.download_file(instance_id, remote_path, local_path)
