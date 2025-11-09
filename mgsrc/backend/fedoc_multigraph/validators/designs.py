"""Pydantic schemas for design endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

ALLOWED_STATUSES = {"draft", "active", "deprecated"}


class DesignBaseModel(BaseModel):
    """Shared optional properties for design payloads."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, min_length=1, max_length=50)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = {"extra": "forbid"}

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        status = value.lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"status must be one of {', '.join(sorted(ALLOWED_STATUSES))}")
        return status

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("metadata must be an object")
        return value


class DesignCreateSchema(DesignBaseModel):
    """Schema for creating a design."""

    name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="draft")
    block_id: Optional[str] = None


class DesignUpdateSchema(DesignBaseModel):
    """Schema for partial design updates."""

    status: Optional[str] = Field(default=None)
    block_id: Optional[str] = Field(default=None)


class DesignQuerySchema(BaseModel):
    """Schema for query parameters when listing designs."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    status: Optional[str] = Field(default=None, min_length=1, max_length=50)
    search: Optional[str] = Field(default=None, min_length=1, max_length=200)

    model_config = {"extra": "forbid"}

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        status = value.lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"status must be one of {', '.join(sorted(ALLOWED_STATUSES))}")
        return status

