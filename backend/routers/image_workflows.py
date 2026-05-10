from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_image_workflow_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import (
    ImageWorkflowConfirmRequest,
    ImageWorkflowCreateRequest,
    ImageWorkflowResponse,
)
from backend.services.image_workflow_service import ImageWorkflowService


router = APIRouter(prefix="/image-workflows", tags=["image-workflows"])


@router.post("/requests", response_model=ImageWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_image_workflow_request(
    payload: ImageWorkflowCreateRequest,
    db: Session = Depends(get_db),
    service: ImageWorkflowService = Depends(get_image_workflow_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ImageWorkflowResponse:
    return await service.create_request(db, identity.wallet_address, payload)


@router.post("/requests/{workflow_id}/confirm", response_model=ImageWorkflowResponse)
async def confirm_image_workflow_request(
    workflow_id: str,
    payload: ImageWorkflowConfirmRequest,
    db: Session = Depends(get_db),
    service: ImageWorkflowService = Depends(get_image_workflow_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> ImageWorkflowResponse:
    return await service.confirm_request(db, workflow_id, identity.wallet_address, payload)


@router.get("/requests/{workflow_id}", response_model=ImageWorkflowResponse)
async def get_image_workflow_request(
    workflow_id: str,
    db: Session = Depends(get_db),
    service: ImageWorkflowService = Depends(get_image_workflow_service),
) -> ImageWorkflowResponse:
    return service._to_workflow_schema(service.get_request(db, workflow_id))
