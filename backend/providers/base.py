from __future__ import annotations

from backend.cloud.contracts.image import ImageBuildPort, ImageShareTicket, ImageSharingPort
from backend.cloud.contracts.instance import InstanceInfo, InstanceLifecyclePort


ImageShareResult = ImageShareTicket


class CloudProvider(InstanceLifecyclePort, ImageSharingPort, ImageBuildPort):
    """兼容旧命名，实际能力定义已迁移到 `backend.cloud.contracts`。"""
