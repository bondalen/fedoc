"""Authentication and authorisation helpers."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Response

ViewFunc = Callable[..., Response]


def require_auth(view: ViewFunc) -> ViewFunc:
    """Placeholder decorator for endpoints that require authentication."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Response:
        # TODO: implement real auth once security model is defined.
        return view(*args, **kwargs)

    return wrapper
