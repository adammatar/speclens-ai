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


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    workspace_id: uuid.UUID = Field(default=uuid.UUID("00000000-0000-4000-8000-000000000001"))
    document_ids: list[uuid.UUID] | None = None
    document_version_ids: list[uuid.UUID] | None = None
    limit: int = Field(default=12, ge=1, le=50)
    debug: bool = False


class SearchHitResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    heading_path: str
    page_number: int | None
    excerpt: str
    start_offset: int
    end_offset: int
    rrf_score: float
    vector_rank: int | None = None
    lexical_rank: int | None = None
    vector_distance: float | None = None
    lexical_rank_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    workspace_id: uuid.UUID
    results: list[SearchHitResponse]
