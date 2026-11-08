"""Local filesystem storage interface stub (Phase 1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings, get_settings


class StorageInterface(ABC):
    """Abstract object storage used by ingestion (Phase 2+)."""

    @abstractmethod
    def put_bytes(self, key: str, data: bytes) -> str:
        """Store bytes at key; return the storage key."""

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        """Read bytes for key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete object at key if present."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if key exists."""


class FilesystemStorage(StorageInterface):
    """Store objects under a local root directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        # Prevent path traversal outside the storage root.
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValueError(f"Invalid storage key: {key}")
        return candidate

    def put_bytes(self, key: str, data: bytes) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_bytes(self, key: str) -> bytes:
        path = self._path_for(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path_for(key).exists()


def get_storage(settings: Settings | None = None) -> StorageInterface:
    """Factory for the configured storage backend."""
    cfg = settings or get_settings()
    if cfg.storage_backend == "filesystem":
        return FilesystemStorage(cfg.storage_local_root)
    raise ValueError(f"Unsupported storage backend: {cfg.storage_backend}")
