"""Object storage abstractions."""

from app.storage.filesystem import FilesystemStorage, StorageInterface, get_storage

__all__ = ["FilesystemStorage", "StorageInterface", "get_storage"]
