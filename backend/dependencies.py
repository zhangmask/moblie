from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.database import get_db_session


def get_notification_service(request: Request):
    return request.app.state.notification_service


def get_agent_service(request: Request):
    return request.app.state.agent_service


def get_instance_service(request: Request):
    return request.app.state.instance_service


def get_file_service(request: Request):
    return request.app.state.file_service


def get_image_workflow_service(request: Request):
    return request.app.state.image_workflow_service


def get_payment_service(request: Request):
    return request.app.state.payment_service


def get_message_service(request: Request):
    return request.app.state.message_service


def get_image_asset_service(request: Request):
    return request.app.state.image_asset_service


def get_review_service(request: Request):
    return request.app.state.review_service


def get_market_service(request: Request):
    return request.app.state.market_service


def get_protocol_service(request: Request):
    return request.app.state.protocol_service


def get_solana_service(request: Request):
    return request.app.state.solana_service


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def ensure_wallet_matches(
    wallet_address: str,
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> WalletIdentity:
    if identity.wallet_address != wallet_address:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="钱包地址与当前请求不匹配",
        )
    return identity
