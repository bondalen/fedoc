"""Pydantic schemas for block endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class BlockBaseModel(BaseModel):
    """Shared properties for block payloads."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    type: Optional[str] = Field(default="concept", min_length=1, max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class BlockCreateSchema(BlockBaseModel):
    """Schema for creating a block."""

    name: str = Field(min_length=1, max_length=200)
    type: str = Field(default="concept", min_length=1, max_length=100)
    parent_id: Optional[str] = None
    relation_type: str = Field(default="contains", min_length=1, max_length=50)


class BlockUpdateSchema(BlockBaseModel):
    """Schema for partial block updates."""

    parent_id: Optional[str] = None
    relation_type: Optional[str] = Field(default=None, min_length=1, max_length=50)

    @field_validator("metadata", mode="before")
    @classmethod
    def allow_none_metadata(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("metadata must be an object")
        return value


class BlockQuerySchema(BaseModel):
    """Schema for query params when listing blocks."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    search: Optional[str] = Field(default=None, min_length=1, max_length=200)

    model_config = {"extra": "forbid"}

