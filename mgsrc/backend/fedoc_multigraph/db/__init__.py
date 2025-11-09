"""Database helpers and Flask integration."""
from __future__ import annotations

from flask import Flask, current_app

from .session import SessionManager

EXTENSION_KEY = "fedoc_multigraph.db_session_manager"


def init_app(app: Flask, dsn: str) -> None:
    """Attach the session manager to the Flask application."""

    app.extensions[EXTENSION_KEY] = SessionManager(dsn)


def get_session_manager() -> SessionManager:
    """Return the configured session manager for the current app."""

    app = current_app._get_current_object()
    manager: SessionManager | None = app.extensions.get(EXTENSION_KEY)  # type: ignore[assignment]
    if manager is None:
        dsn = app.config.get("FEDOC_DATABASE_URL")
        if not dsn:
            raise RuntimeError("Database URL is not configured")
        manager = SessionManager(dsn)
        app.extensions[EXTENSION_KEY] = manager

    return manager

