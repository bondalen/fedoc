"""Validation helpers built on top of Pydantic."""
from __future__ import annotations

from typing import Any, Dict, Type, TypeVar

from flask import Request
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_json(model: Type[ModelT], request: Request) -> ModelT:
    """Validate request JSON payload against ``model``."""

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise ValueError("Request payload must be a JSON object.")
    return model.model_validate(data)


def validate_query(model: Type[ModelT], request_args: Any) -> ModelT:
    """Validate query parameters."""

    if hasattr(request_args, "to_dict"):
        data = request_args.to_dict(flat=True)
    else:
        data = dict(request_args)
    return model.model_validate(data)
