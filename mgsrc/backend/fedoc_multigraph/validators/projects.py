"""Pydantic schemas for project endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectBaseModel(BaseModel):
    """Shared optional properties for project payloads."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    design_edge_ids: Optional[List[str]] = Field(default=None)

    model_config = {"extra": "forbid"}


class ProjectCreateSchema(ProjectBaseModel):
    """Schema for creating a project."""

    name: str = Field(min_length=1, max_length=200)


class ProjectUpdateSchema(ProjectBaseModel):
    """Schema for partial project updates."""


class ProjectQuerySchema(BaseModel):
    """Schema for query parameters when listing projects."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    search: Optional[str] = Field(default=None, min_length=1, max_length=200)

    model_config = {"extra": "forbid"}

