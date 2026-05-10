from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FileTransferResult:
    path: str
    size_bytes: int
    checksum: str | None = None


class FileTransferPort(ABC):
    @abstractmethod
    async def upload_file(
        self,
        instance_id: str,
        local_path: str,
        remote_path: str,
    ) -> FileTransferResult:
        raise NotImplementedError

    @abstractmethod
    async def download_file(
        self,
        instance_id: str,
        remote_path: str,
        local_path: str,
    ) -> FileTransferResult:
        raise NotImplementedError
