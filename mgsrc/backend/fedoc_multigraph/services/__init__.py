"""Service factory helpers."""
from __future__ import annotations

from flask import current_app

from ..config.settings import Settings
from ..db import get_session_manager
from ..db.repositories.blocks import BlocksRepository
from .blocks import BlocksService

BLOCKS_SERVICE_KEY = "fedoc_multigraph.blocks_service"


def get_blocks_service() -> BlocksService:
    """Return a BlocksService instance cached on the application."""

    app = current_app._get_current_object()
    service: BlocksService | None = app.extensions.get(BLOCKS_SERVICE_KEY)  # type: ignore[assignment]
    if service is None:
        settings = app.config.get("FEDOC_SETTINGS", Settings.from_env())
        repository = BlocksRepository(get_session_manager(), settings=settings)
        default_limit = getattr(settings, "api_default_limit", 50)
        service = BlocksService(repository, default_limit=default_limit)
        app.extensions[BLOCKS_SERVICE_KEY] = service

    return service

