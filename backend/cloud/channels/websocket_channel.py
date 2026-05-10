from __future__ import annotations

from fastapi import WebSocket

from backend.cloud.contracts.notification import NotificationMessage


class WebSocketNotificationChannel:
    channel_name = "websocket"

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, target: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(target, set()).add(websocket)

    def disconnect(self, target: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(target)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(target, None)

    async def send(self, message: NotificationMessage) -> None:
        for websocket in list(self._connections.get(message.target, set())):
            await websocket.send_json(
                {
                    "channel": message.channel,
                    "target": message.target,
                    "type": message.event_type,
                    "payload": message.payload,
                }
            )
