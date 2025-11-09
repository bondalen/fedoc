"""Middleware utilities for the Flask app."""
from __future__ import annotations

from flask import Flask


def register_middlewares(app: Flask) -> None:
    """Attach middlewares to the Flask application."""

    # Placeholder: add middleware (e.g., logging, request id) here when needed.
    app.logger.debug("Middleware stack initialised")
