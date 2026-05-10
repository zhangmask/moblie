from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.models.database import AssetFileRecord, UserImageRecord
from backend.models.schemas import AssetFileResponse
from backend.services.notification_service import NotificationService


class ImageAssetService:
    def __init__(self, storage_root: Path, notification_service: NotificationService) -> None:
        self.storage_root = storage_root
        self.notification_service = notification_service

    async def store_upload(
        self,
        db: Session,
        image: UserImageRecord,
        upload: UploadFile,
    ) -> AssetFileResponse:
        filename = Path(upload.filename or "upload.bin").name
        contents = await upload.read()
        target_dir = self.storage_root / "images" / image.id / "workspace"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(contents)
        record = AssetFileRecord(
            owner_wallet=image.owner_wallet,
            target_type="image",
            target_id=image.id,
            filename=filename,
            size_bytes=len(contents),
            direction="upload",
        )
        db.add(record)
        db.commit()
        await self.notification_service.publish(
            db,
            image.owner_wallet,
            "image_file_uploaded",
            {"image_id": image.id, "filename": filename},
        )
        return AssetFileResponse(
            target_type="image",
            target_id=image.id,
            filename=filename,
            direction="upload",
            size_bytes=len(contents),
        )

    def resolve_download_path(self, db: Session, image: UserImageRecord, filename: str) -> Path:
        safe_name = Path(filename).name
        workspace_path = self.storage_root / "images" / image.id / "workspace" / safe_name
        output_path = self.storage_root / "images" / image.id / "output" / safe_name
        if not output_path.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                f"demo output for image {image.image_name}: {safe_name}\n",
                encoding="utf-8",
            )
        for path in [output_path, workspace_path]:
            if path.exists():
                self.record_transfer(db, image, path.name, path.stat().st_size, "download")
                return path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜像文件不存在")

    def record_transfer(
        self,
        db: Session,
        image: UserImageRecord,
        filename: str,
        size_bytes: int,
        direction: str,
    ) -> None:
        record = AssetFileRecord(
            owner_wallet=image.owner_wallet,
            target_type="image",
            target_id=image.id,
            filename=filename,
            size_bytes=size_bytes,
            direction=direction,
        )
        db.add(record)
        db.commit()
