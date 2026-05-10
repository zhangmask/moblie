from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_file_service, get_instance_service
from backend.middleware.wallet_auth import WalletIdentity, require_wallet_identity
from backend.models.schemas import FileUploadResponse
from backend.services.file_service import FileService
from backend.services.instance_service import InstanceService


router = APIRouter(prefix="/instances/{instance_id}/files", tags=["files"])


@router.post("", response_model=FileUploadResponse)
async def upload_file(
    instance_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    file_service: FileService = Depends(get_file_service),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
) -> FileUploadResponse:
    record = instance_service.get_instance(db, instance_id)
    instance_service.ensure_owner(record, identity.wallet_address)
    return await file_service.store_upload(db, record, file)


@router.get("/{filename}")
async def download_file(
    instance_id: str,
    filename: str,
    db: Session = Depends(get_db),
    file_service: FileService = Depends(get_file_service),
    instance_service: InstanceService = Depends(get_instance_service),
    identity: WalletIdentity = Depends(require_wallet_identity),
):
    record = instance_service.get_instance(db, instance_id)
    instance_service.ensure_owner(record, identity.wallet_address)
    path = await file_service.prepare_download(record, filename)
    file_service.record_download(db, instance_id, path.name, path.stat().st_size)
    return FileResponse(path, filename=path.name)
