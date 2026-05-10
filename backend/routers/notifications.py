from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_notification_service
from backend.models.schemas import NotificationEvent
from backend.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/{wallet}", response_model=list[NotificationEvent])
async def list_notifications(
    wallet: str,
    db: Session = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationEvent]:
    return notification_service.list_recent(db, wallet)


@router.websocket("/{wallet}")
async def notifications_ws(wallet: str, websocket: WebSocket) -> None:
    notification_service: NotificationService = websocket.app.state.notification_service
    await notification_service.connect(wallet, websocket)
    await websocket.send_json({"type": "connected", "wallet": wallet})
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong", "wallet": wallet})
    except WebSocketDisconnect:
        notification_service.disconnect(wallet, websocket)
