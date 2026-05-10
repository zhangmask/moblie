from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_instance_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import HiredInstanceResponse
from backend.services.instance_service import InstanceService


router = APIRouter(prefix="/hired", tags=["hired"])


@router.get("", response_model=list[HiredInstanceResponse])
async def list_hired_instances(
    db: Session = Depends(get_db),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[HiredInstanceResponse]:
    return instance_service.list_hired(db, identity.wallet_address)
