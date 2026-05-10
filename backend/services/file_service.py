from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.cloud.orchestrators.file_exchange import FileExchangeOrchestrator
from backend.models.database import InstanceRecord
from backend.models.database import FileRecord
from backend.models.schemas import FileUploadResponse


class FileService:
    def __init__(self, storage_root: Path, file_exchange: FileExchangeOrchestrator) -> None:
        self.storage_root = storage_root
        self.file_exchange = file_exchange

    async def store_upload(
        self,
        db: Session,
        instance: InstanceRecord,
        upload: UploadFile,
    ) -> FileUploadResponse:
        filename = Path(upload.filename or "upload.bin").name
        contents = await upload.read()
        target_dir = self.storage_root / instance.id / "workspace"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(contents)
        await self.file_exchange.upload_file(
            provider_name=instance.provider_name,
            instance_id=instance.provider_instance_id or instance.id,
            local_path=str(target_path),
            remote_path=f"/workspace/{filename}",
        )

        record = FileRecord(
            instance_id=instance.id,
            filename=filename,
            size_bytes=len(contents),
            direction="upload",
        )
        db.add(record)
        db.commit()
        return FileUploadResponse(
            instance_id=instance.id,
            filename=filename,
            direction="upload",
            size_bytes=len(contents),
        )

    async def prepare_download(
        self,
        instance: InstanceRecord,
        filename: str,
    ) -> Path:
        safe_name = Path(filename).name
        output_dir = self.storage_root / instance.id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / safe_name
        if not output_path.exists():
            await self.file_exchange.download_file(
                provider_name=instance.provider_name,
                instance_id=instance.provider_instance_id or instance.id,
                remote_path=f"/output/{safe_name}",
                local_path=str(output_path),
            )
        candidates = [output_path, self.storage_root / instance.id / "workspace" / safe_name]
        for path in candidates:
            if path.exists():
                return path
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在，当前只支持下载 workspace/output 中的文件",
        )

    def record_download(self, db: Session, instance_id: str, filename: str, size_bytes: int) -> None:
        record = FileRecord(
            instance_id=instance_id,
            filename=filename,
            size_bytes=size_bytes,
            direction="download",
        )
        db.add(record)
        db.commit()
