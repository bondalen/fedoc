"""API blueprint registration."""
from __future__ import annotations

from flask import Blueprint, Flask, jsonify

from .blocks import blocks_bp
from .designs import designs_bp

API_PREFIX = "/api"


def register_api(app: Flask) -> None:
    """Register all API blueprints with the Flask app."""

    health_bp = Blueprint("health", __name__, url_prefix=API_PREFIX)

    @health_bp.get("/health")
    def healthcheck() -> tuple[str, int]:
        return jsonify({"status": "ok"}), 200

    app.register_blueprint(health_bp)
    app.register_blueprint(blocks_bp)
    app.register_blueprint(designs_bp)
