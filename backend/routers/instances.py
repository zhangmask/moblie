from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_instance_service, get_protocol_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import (
    FireAgentOsResponse,
    InstanceCreateRequest,
    InstanceResponse,
    TaskDispatchRequest,
    TaskDispatchResponse,
)
from backend.services.instance_service import InstanceService
from backend.services.protocol_service import ProtocolService


router = APIRouter(prefix="/instances", tags=["instances"])


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: InstanceCreateRequest,
    db: Session = Depends(get_db),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> InstanceResponse:
    if identity.wallet_address != payload.owner_wallet:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Wallet-Address 必须与 owner_wallet 一致",
        )
    return await instance_service.create_instance(db, payload)


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: str,
    db: Session = Depends(get_db),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> InstanceResponse:
    record = instance_service.get_instance(db, instance_id)
    instance_service.ensure_owner(record, identity.wallet_address)
    return instance_service._to_schema(record)


@router.delete("/{instance_id}", response_model=InstanceResponse)
async def destroy_instance(
    instance_id: str,
    db: Session = Depends(get_db),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> InstanceResponse:
    record = instance_service.get_instance(db, instance_id)
    instance_service.ensure_owner(record, identity.wallet_address)
    return await instance_service.destroy_instance(db, instance_id)


@router.post("/{instance_id}/fire", response_model=FireAgentOsResponse)
async def fire_agent_os(
    instance_id: str,
    db: Session = Depends(get_db),
    protocol_service: ProtocolService = Depends(get_protocol_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> FireAgentOsResponse:
    return await protocol_service.fire_agent_os(db, instance_id, identity.wallet_address)


@router.post("/{instance_id}/task", response_model=TaskDispatchResponse)
async def dispatch_task(
    instance_id: str,
    payload: TaskDispatchRequest,
    db: Session = Depends(get_db),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> TaskDispatchResponse:
    record = instance_service.get_instance(db, instance_id)
    instance_service.ensure_owner(record, identity.wallet_address)
    return await instance_service.dispatch_task(db, instance_id, payload)
