"""Repository helpers."""
from __future__ import annotations

from dataclasses import dataclass

from ..session import SessionManager


@dataclass(slots=True)
class RepositoryContext:
    """Shared context for repositories."""

    session_manager: SessionManager
    graph_name: str

