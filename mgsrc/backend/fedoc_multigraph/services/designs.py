"""Business logic for design management."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..db.repositories.designs import DesignsRepository
from ..errors.designs import DesignConflictError, DesignNotFoundError
from ..validators.designs import DesignCreateSchema, DesignQuerySchema, DesignUpdateSchema


class _Unset:
    pass


UNSET = _Unset()


class DesignsService:
    """Encapsulates business rules for designs."""

    def __init__(self, repository: DesignsRepository, *, default_limit: int = 50) -> None:
        self._repository = repository
        self._default_limit = default_limit

    def list_designs(self, query: DesignQuerySchema) -> Dict[str, Any]:
        limit = query.limit if query.limit is not None else self._default_limit
        offset = query.offset if query.offset is not None else 0
        items = self._repository.list(limit=limit, offset=offset)
        items = self._apply_filters(items, query)
        return {
            "items": items[:limit],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
            },
        }

    def get_design(self, design_id: str) -> Dict[str, Any]:
        design = self._repository.get(design_id)
        if not design:
            raise DesignNotFoundError(design_id)
        return design

    def create_design(self, payload: DesignCreateSchema) -> Dict[str, Any]:
        prepared = payload.model_dump()
        block_id = prepared.pop("block_id", None)
        if not prepared.get("status"):
            prepared["status"] = "draft"
        if prepared.get("created_at") is None:
            prepared["created_at"] = datetime.now(tz=timezone.utc).isoformat()
        elif isinstance(prepared["created_at"], datetime):
            prepared["created_at"] = prepared["created_at"].astimezone(timezone.utc).isoformat()

        try:
            design = self._repository.create(prepared, block_id=block_id)
        except RuntimeError as exc:
            raise DesignConflictError(str(exc)) from exc
        return design

    def update_design(self, design_id: str, payload: DesignUpdateSchema) -> Dict[str, Any]:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_design(design_id)

        block_id = updates.pop("block_id", UNSET)
        if "created_at" in updates:
            created_at = updates["created_at"]
            if created_at is None:
                updates.pop("created_at")
            elif isinstance(created_at, datetime):
                updates["created_at"] = created_at.astimezone(timezone.utc).isoformat()

        try:
            design = self._repository.update(
                design_id,
                updates,
                block_id=block_id if block_id is not UNSET else None,
                block_id_provided=block_id is not UNSET,
            )
        except RuntimeError as exc:
            raise DesignConflictError(str(exc)) from exc

        if not design:
            raise DesignNotFoundError(design_id)
        return design

    def delete_design(self, design_id: str) -> None:
        deleted = self._repository.delete(design_id)
        if not deleted:
            raise DesignNotFoundError(design_id)

    def _apply_filters(self, items: List[Dict[str, Any]], params: DesignQuerySchema) -> List[Dict[str, Any]]:
        filtered = items
        if params.status:
            filtered = [item for item in filtered if item["properties"].get("status") == params.status]
        if params.search:
            needle = params.search.lower()
            filtered = [
                item
                for item in filtered
                if needle in (item["properties"].get("name", "").lower())
                or needle in (item["properties"].get("description", "").lower())
            ]
        return filtered

