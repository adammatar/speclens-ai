"""Pydantic response/request schemas for the HTTP API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadAcceptedResponse(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_id: uuid.UUID
    sha256: str
    status: str = "accepted"


class DuplicateUploadResponse(BaseModel):
    detail: str = "Duplicate document content"
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    sha256: str


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_version_id: uuid.UUID
    status: str
    progress_pct: int
    error_message: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    text: str
    heading_path: str
    page_number: int | None
    start_offset: int
    end_offset: int
    token_count: int


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    filename: str
    content_type: str
    byte_size: int
    sha256: str
    status: str
    error_message: str | None = None
    page_count: int | None = None
    created_at: datetime
    chunk_count: int = 0


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse] = Field(default_factory=list)


class ReprocessResponse(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_id: uuid.UUID
    status: str = "queued"
