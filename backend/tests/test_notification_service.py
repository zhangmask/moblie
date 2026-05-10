from __future__ import annotations

import asyncio

from backend.cloud.contracts.notification import NotificationMessage
from backend.services.notification_service import NotificationService


class FakeChannel:
    def __init__(self) -> None:
        self.messages: list[NotificationMessage] = []

    async def send(self, message: NotificationMessage) -> None:
        self.messages.append(message)


def test_notification_service_accepts_notification_message(db_session) -> None:
    async def run_test():
        channel = FakeChannel()
        service = NotificationService({"websocket": channel})
        message = NotificationMessage(
            channel="websocket",
            target="wallet-a",
            event_type="instance_ready",
            payload={"instance_id": "inst-1"},
        )
        event = await service.send(message, db=db_session)
        return event, channel

    event, channel = asyncio.run(run_test())
    assert event.wallet == "wallet-a"
    assert event.type == "instance_ready"
    assert channel.messages[0].payload["instance_id"] == "inst-1"
