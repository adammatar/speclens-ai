"""Ingestion-domain errors."""


class ParseError(ValueError):
    """Raised when a document cannot be parsed."""


class DuplicateDocumentError(ValueError):
    """Raised when an upload matches an existing SHA-256 in the workspace."""

    def __init__(self, *, document_id: str, document_version_id: str, sha256: str) -> None:
        super().__init__(f"Duplicate content sha256={sha256}")
        self.document_id = document_id
        self.document_version_id = document_version_id
        self.sha256 = sha256


class NotFoundError(LookupError):
    """Raised when a document or version cannot be found."""
