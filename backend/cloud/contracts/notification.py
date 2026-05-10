from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationMessage:
    channel: str
    target: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


class NotificationPort(ABC):
    @abstractmethod
    async def send(self, message: NotificationMessage) -> None:
        raise NotImplementedError
