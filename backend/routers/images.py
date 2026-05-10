from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.dependencies import (
    get_db,
    get_image_asset_service,
    get_image_workflow_service,
    get_message_service,
)
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import AssetFileResponse, ImageMessageCreateRequest, MessageResponse, UserImageResponse
from backend.services.image_asset_service import ImageAssetService
from backend.services.image_workflow_service import ImageWorkflowService
from backend.services.message_service import MessageService


router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=list[UserImageResponse])
async def list_my_images(
    db: Session = Depends(get_db),
    service: ImageWorkflowService = Depends(get_image_workflow_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[UserImageResponse]:
    return service.list_user_images(db, identity.wallet_address)


@router.get("/{image_id}", response_model=UserImageResponse)
async def get_my_image(
    image_id: str,
    db: Session = Depends(get_db),
    service: ImageWorkflowService = Depends(get_image_workflow_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> UserImageResponse:
    record = service.get_user_image(db, image_id)
    service.ensure_owner(record, identity.wallet_address)
    return service._to_user_image_schema(record)


@router.post("/{image_id}/messages", response_model=list[MessageResponse])
async def send_image_message(
    image_id: str,
    payload: ImageMessageCreateRequest,
    db: Session = Depends(get_db),
    image_service: ImageWorkflowService = Depends(get_image_workflow_service),
    message_service: MessageService = Depends(get_message_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[MessageResponse]:
    image = image_service.get_user_image(db, image_id)
    image_service.ensure_owner(image, identity.wallet_address)
    return await message_service.send_image_message(db, image, payload)


@router.get("/{image_id}/messages", response_model=list[MessageResponse])
async def list_image_messages(
    image_id: str,
    db: Session = Depends(get_db),
    image_service: ImageWorkflowService = Depends(get_image_workflow_service),
    message_service: MessageService = Depends(get_message_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> list[MessageResponse]:
    image = image_service.get_user_image(db, image_id)
    image_service.ensure_owner(image, identity.wallet_address)
    return message_service.list_image_messages(db, image_id)


@router.post("/{image_id}/files", response_model=AssetFileResponse)
async def upload_image_file(
    image_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    image_service: ImageWorkflowService = Depends(get_image_workflow_service),
    asset_service: ImageAssetService = Depends(get_image_asset_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> AssetFileResponse:
    image = image_service.get_user_image(db, image_id)
    image_service.ensure_owner(image, identity.wallet_address)
    return await asset_service.store_upload(db, image, file)


@router.get("/{image_id}/files/{filename}")
async def download_image_file(
    image_id: str,
    filename: str,
    db: Session = Depends(get_db),
    image_service: ImageWorkflowService = Depends(get_image_workflow_service),
    asset_service: ImageAssetService = Depends(get_image_asset_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
):
    image = image_service.get_user_image(db, image_id)
    image_service.ensure_owner(image, identity.wallet_address)
    path = asset_service.resolve_download_path(db, image, filename)
    return FileResponse(path, filename=path.name)
