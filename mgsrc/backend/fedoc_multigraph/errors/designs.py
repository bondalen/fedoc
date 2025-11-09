"""Domain-specific exceptions for design operations."""
from __future__ import annotations


class DesignError(RuntimeError):
    """Base class for design-related errors."""

    status_code = 400
    error_code = "design_error"

    def to_response(self) -> dict[str, str]:
        return {"error": self.error_code, "message": str(self)}


class DesignNotFoundError(DesignError):
    """Raised when a design cannot be located."""

    status_code = 404
    error_code = "design_not_found"

    def __init__(self, design_id: str) -> None:
        super().__init__(f"Design '{design_id}' not found.")
        self.design_id = design_id


class DesignConflictError(DesignError):
    """Raised when a design violates constraints (e.g. duplicate name)."""

    status_code = 409
    error_code = "design_conflict"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)

