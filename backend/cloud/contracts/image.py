from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageShareTicket:
    provider_name: str
    image_ref: str
    target_ref: str
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class ImageSharingPort(ABC):
    @abstractmethod
    async def share_image(self, image_ref: str, target_ref: str) -> ImageShareTicket:
        raise NotImplementedError

    @abstractmethod
    async def revoke_shared_image(self, image_ref: str, target_ref: str) -> bool:
        raise NotImplementedError


class ImageBuildPort(ABC):
    @abstractmethod
    async def create_custom_image(self, instance_id: str, image_name: str) -> str:
        raise NotImplementedError
