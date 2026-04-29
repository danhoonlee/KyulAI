"""Domain exceptions for the service layer.

Services raise these; API route handlers catch them and convert to
HTTPException so that HTTP semantics stay out of the service layer.
"""

from uuid import UUID


class KyulAIError(Exception):
    """Base exception for all KyulAI backend errors."""


class NotFoundError(KyulAIError):
    def __init__(self, resource: str, id: UUID | str) -> None:
        super().__init__(f"{resource} '{id}' not found")
        self.resource = resource
        self.id = id


class ConflictError(KyulAIError):
    """Raised when an operation conflicts with existing state (e.g. duplicate)."""


class InvalidStateError(KyulAIError):
    """Raised when an operation is invalid for the resource's current state."""


class StorageError(KyulAIError):
    """Raised on object storage (MinIO/S3) failures."""


class ParseError(KyulAIError):
    """Raised when a CAE file cannot be parsed into a UnifiedCAERecord."""
