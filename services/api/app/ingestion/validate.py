"""Upload validation for supported document types."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.types import SupportedKind

# 50 MiB default upload cap for Phase 2.
DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

ALLOWED_EXTENSIONS: dict[str, SupportedKind] = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".docx": "docx",
    ".pdf": "pdf",
}

ALLOWED_CONTENT_TYPES: dict[str, SupportedKind] = {
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
    "text/plain": "markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
}


class UploadValidationError(ValueError):
    """Raised when an upload fails MIME/extension/size checks."""


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    filename: str
    content_type: str
    kind: SupportedKind
    size: int


def _extension(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1]
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def validate_upload(
    *,
    filename: str,
    content_type: str | None,
    size: int,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> ValidatedUpload:
    """Validate filename extension, content type, and size."""
    if size <= 0:
        raise UploadValidationError("Empty uploads are not allowed")
    if size > max_bytes:
        raise UploadValidationError(f"File exceeds max size of {max_bytes} bytes")

    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            f"Unsupported file extension '{ext or '(none)'}'. Allowed: .md, .markdown, .docx, .pdf"
        )
    kind_from_ext = ALLOWED_EXTENSIONS[ext]

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if not normalized_type:
        # Browsers sometimes omit type; trust extension after size/ext checks.
        normalized_type = {
            "markdown": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
        }[kind_from_ext]
    elif normalized_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(f"Unsupported content type '{normalized_type}'")
    else:
        kind_from_type = ALLOWED_CONTENT_TYPES[normalized_type]
        if kind_from_type != kind_from_ext and not (
            kind_from_ext == "markdown" and normalized_type == "text/plain"
        ):
            raise UploadValidationError(
                f"Content type '{normalized_type}' does not match extension '{ext}'"
            )

    return ValidatedUpload(
        filename=filename.rsplit("/", 1)[-1],
        content_type=normalized_type,
        kind=kind_from_ext,
        size=size,
    )
