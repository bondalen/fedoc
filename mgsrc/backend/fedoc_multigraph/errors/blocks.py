"""Domain-specific exceptions for block operations."""
from __future__ import annotations


class BlockError(RuntimeError):
    """Base class for block-related errors."""

    status_code = 400
    error_code = "block_error"

    def to_response(self) -> dict[str, str]:
        return {"error": self.error_code, "message": str(self)}


class BlockNotFoundError(BlockError):
    """Raised when a block cannot be located."""

    status_code = 404
    error_code = "block_not_found"

    def __init__(self, block_id: str) -> None:
        super().__init__(f"Block '{block_id}' not found.")
        self.block_id = block_id


class BlockConflictError(BlockError):
    """Raised when a block violates constraints (e.g. duplicate name)."""

    status_code = 409
    error_code = "block_conflict"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)

