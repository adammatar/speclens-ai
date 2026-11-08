"""Filesystem storage stub tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.filesystem import FilesystemStorage


def test_put_get_delete_roundtrip(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    key = "workspace/demo/file.txt"
    storage.put_bytes(key, b"hello")
    assert storage.exists(key)
    assert storage.get_bytes(key) == b"hello"
    storage.delete(key)
    assert not storage.exists(key)


def test_rejects_path_traversal(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.put_bytes("../escape.txt", b"nope")
