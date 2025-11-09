"""Error handlers for the backend application."""
from __future__ import annotations

from flask import Flask, jsonify
from pydantic import ValidationError

from .blocks import BlockConflictError, BlockError, BlockNotFoundError
from .designs import DesignConflictError, DesignError, DesignNotFoundError


def _serialise_validation_errors(errors: list[dict]) -> list[dict]:
    serialised: list[dict] = []
    for error in errors:
        entry = dict(error)
        ctx = entry.get("ctx")
        if isinstance(ctx, dict):
            entry["ctx"] = {key: (str(value) if isinstance(value, Exception) else value) for key, value in ctx.items()}
        serialised.append(entry)
    return serialised


def register_error_handlers(app: Flask) -> None:
    """Register default error handlers."""

    @app.errorhandler(404)
    def _not_found(_: Exception):  # type: ignore[override]
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def _internal_error(_: Exception):  # type: ignore[override]
        return jsonify({"error": "internal_server_error"}), 500

    @app.errorhandler(BlockError)
    def _handle_block_error(exc: BlockError):
        return jsonify(exc.to_response()), exc.status_code

    @app.errorhandler(DesignError)
    def _handle_design_error(exc: DesignError):
        return jsonify(exc.to_response()), exc.status_code

    @app.errorhandler(ValidationError)
    def _handle_validation_error(exc: ValidationError):
        return jsonify({"error": "validation_error", "details": _serialise_validation_errors(exc.errors())}), 422

    @app.errorhandler(ValueError)
    def _handle_value_error(exc: ValueError):
        return jsonify({"error": "validation_error", "message": str(exc)}), 400
