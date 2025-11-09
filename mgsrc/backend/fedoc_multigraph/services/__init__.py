"""Service factory helpers."""
from __future__ import annotations

from flask import current_app

from ..config.settings import Settings
from ..db import get_session_manager
from ..db.repositories.blocks import BlocksRepository
from ..db.repositories.designs import DesignsRepository
from .blocks import BlocksService
from .designs import DesignsService

BLOCKS_SERVICE_KEY = "fedoc_multigraph.blocks_service"
DESIGNS_SERVICE_KEY = "fedoc_multigraph.designs_service"


def _get_settings():
    app = current_app._get_current_object()
    return app.config.get("FEDOC_SETTINGS", Settings.from_env())


def get_blocks_service() -> BlocksService:
    """Return a BlocksService instance cached on the application."""

    app = current_app._get_current_object()
    service: BlocksService | None = app.extensions.get(BLOCKS_SERVICE_KEY)  # type: ignore[assignment]
    if service is None:
        settings = _get_settings()
        repository = BlocksRepository(get_session_manager(), settings=settings)
        default_limit = getattr(settings, "api_default_limit", 50)
        service = BlocksService(repository, default_limit=default_limit)
        app.extensions[BLOCKS_SERVICE_KEY] = service

    return service


def get_designs_service() -> DesignsService:
    """Return a DesignsService instance cached on the application."""

    app = current_app._get_current_object()
    service: DesignsService | None = app.extensions.get(DESIGNS_SERVICE_KEY)  # type: ignore[assignment]
    if service is None:
        settings = _get_settings()
        repository = DesignsRepository(get_session_manager(), settings=settings)
        default_limit = getattr(settings, "api_default_limit", 50)
        service = DesignsService(repository, default_limit=default_limit)
        app.extensions[DESIGNS_SERVICE_KEY] = service

    return service

