"""Domain-specific exceptions for project operations."""
from __future__ import annotations


class ProjectError(RuntimeError):
    """Base class for project-related errors."""

    status_code = 400
    error_code = "project_error"

    def to_response(self) -> dict[str, str]:
        return {"error": self.error_code, "message": str(self)}


class ProjectNotFoundError(ProjectError):
    """Raised when a project cannot be located."""

    status_code = 404
    error_code = "project_not_found"

    def __init__(self, project_id: int) -> None:
        super().__init__(f"Project '{project_id}' not found.")
        self.project_id = project_id


class ProjectConflictError(ProjectError):
    """Raised when creating/updating a project violates constraints."""

    status_code = 409
    error_code = "project_conflict"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)

