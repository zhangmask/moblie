from __future__ import annotations

from uuid import uuid4

from backend.cloud.contracts.file_transfer import FileTransferPort, FileTransferResult
from backend.cloud.contracts.image import ImageBuildPort, ImageShareTicket, ImageSharingPort
from backend.cloud.contracts.instance import InstanceInfo, InstanceLifecyclePort, InstanceSpec


class TencentCloudProvider(
    InstanceLifecyclePort,
    ImageSharingPort,
    ImageBuildPort,
    FileTransferPort,
):
    """腾讯云示例适配器。

    该类保留为后续真实接入 tccli / SDK 的入口，但默认不注册到主流程。
    """

    provider_name = "tencent"

    def __init__(self, secret_id: str, secret_key: str, region: str = "ap-guangzhou") -> None:
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.stub_mode = not (secret_id and secret_key)

    async def create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        instance_id = await self._run_instances(
            image_ref=spec.image_ref,
            instance_type=spec.instance_type,
            security_groups=spec.security_groups,
            network_ref=spec.network_ref,
            user_data=spec.user_data,
        )
        return InstanceInfo(
            provider_name=self.provider_name,
            instance_id=instance_id,
            public_ip="127.0.0.1",
            private_ip="10.0.0.8",
            status="running",
            raw={"region": self.region},
        )

    async def destroy_instance(self, instance_id: str) -> bool:
        await self._terminate_instances(instance_id)
        return True

    async def get_instance_status(self, instance_id: str) -> InstanceInfo:
        return InstanceInfo(
            provider_name=self.provider_name,
            instance_id=instance_id,
            public_ip="127.0.0.1",
            private_ip="10.0.0.8",
            status="running",
            raw={"region": self.region},
        )

    async def share_image(self, image_ref: str, target_ref: str) -> ImageShareTicket:
        action = "stub_share" if self.stub_mode else "share"
        return ImageShareTicket(
            provider_name=self.provider_name,
            image_ref=image_ref,
            target_ref=target_ref,
            status=action,
            raw={"region": self.region},
        )

    async def revoke_shared_image(self, image_ref: str, target_ref: str) -> bool:
        _ = ("stub_revoke" if self.stub_mode else "revoke", image_ref, target_ref, self.region)
        return True

    async def create_custom_image(self, instance_id: str, image_name: str) -> str:
        return f"img-{image_name.lower()}-{instance_id[-6:]}"

    async def upload_file(
        self,
        instance_id: str,
        local_path: str,
        remote_path: str,
    ) -> FileTransferResult:
        _ = (instance_id, remote_path)
        return FileTransferResult(path=local_path, size_bytes=0)

    async def download_file(
        self,
        instance_id: str,
        remote_path: str,
        local_path: str,
    ) -> FileTransferResult:
        _ = (instance_id, remote_path)
        return FileTransferResult(path=local_path, size_bytes=0)

    async def _run_instances(
        self,
        image_ref: str,
        instance_type: str,
        security_groups: list[str],
        network_ref: str,
        user_data: str | None,
    ) -> str:
        _ = (image_ref, instance_type, security_groups, network_ref, user_data)
        return f"ins-{uuid4().hex[:8]}"

    async def _terminate_instances(self, instance_id: str) -> None:
        _ = instance_id
