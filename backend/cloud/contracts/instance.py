from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InstanceSpec:
    image_ref: str
    instance_type: str
    network_ref: str
    security_groups: list[str] = field(default_factory=list)
    user_data: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstanceInfo:
    provider_name: str
    instance_id: str
    status: str
    public_ip: str | None = None
    private_ip: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class InstanceLifecyclePort(ABC):
    @abstractmethod
    async def create_instance(self, spec: InstanceSpec) -> InstanceInfo:
        raise NotImplementedError

    @abstractmethod
    async def destroy_instance(self, instance_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_instance_status(self, instance_id: str) -> InstanceInfo:
        raise NotImplementedError
