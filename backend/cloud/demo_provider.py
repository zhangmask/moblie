from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.cloud.contracts.file_transfer import FileTransferPort, FileTransferResult
from backend.cloud.contracts.image import ImageBuildPort, ImageShareTicket, ImageSharingPort
from backend.cloud.contracts.instance import InstanceInfo, InstanceLifecyclePort, InstanceSpec


class DemoCloudProvider(
    InstanceLifecyclePort,
    ImageSharingPort,
    ImageBuildPort,
    FileTransferPort,
):
    """与具体云厂商无关的本地演示 provider。"""

    provider_name = "demo"

    async def create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        return InstanceInfo(
            provider_name=self.provider_name,
            instance_id=f"demo-{uuid4().hex[:8]}",
            status="running",
            public_ip="127.0.0.1",
            private_ip="10.0.0.8",
            raw={"image_ref": spec.image_ref, "network_ref": spec.network_ref},
        )

    async def destroy_instance(self, instance_id: str) -> bool:
        _ = instance_id
        return True

    async def get_instance_status(self, instance_id: str) -> InstanceInfo:
        return InstanceInfo(
            provider_name=self.provider_name,
            instance_id=instance_id,
            status="running",
            public_ip="127.0.0.1",
            private_ip="10.0.0.8",
        )

    async def share_image(self, image_ref: str, target_ref: str) -> ImageShareTicket:
        return ImageShareTicket(
            provider_name=self.provider_name,
            image_ref=image_ref,
            target_ref=target_ref,
            status="shared",
            raw={"mode": "demo"},
        )

    async def revoke_shared_image(self, image_ref: str, target_ref: str) -> bool:
        _ = (image_ref, target_ref)
        return True

    async def create_custom_image(self, instance_id: str, image_name: str) -> str:
        return f"demo-image-{image_name.lower()}-{instance_id[-4:]}"

    async def upload_file(
        self,
        instance_id: str,
        local_path: str,
        remote_path: str,
    ) -> FileTransferResult:
        size_bytes = Path(local_path).stat().st_size if Path(local_path).exists() else 0
        _ = (instance_id, remote_path)
        return FileTransferResult(path=local_path, size_bytes=size_bytes)

    async def download_file(
        self,
        instance_id: str,
        remote_path: str,
        local_path: str,
    ) -> FileTransferResult:
        target = Path(local_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = f"demo download from {instance_id}:{remote_path}\n"
        target.write_text(content, encoding="utf-8")
        return FileTransferResult(path=str(target), size_bytes=len(content.encode("utf-8")))
