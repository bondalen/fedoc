"""Business logic for block management."""
from __future__ import annotations

from typing import Any, Dict, List

from ..errors.blocks import BlockConflictError, BlockNotFoundError
from ..validators.blocks import BlockCreateSchema, BlockQuerySchema, BlockUpdateSchema
from ..db.repositories.blocks import BlocksRepository


class BlocksService:
    """Encapsulates business rules for blocks."""

    def __init__(self, repository: BlocksRepository, *, default_limit: int = 50) -> None:
        self._repository = repository
        self._default_limit = default_limit

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def list_blocks(self, query: BlockQuerySchema) -> Dict[str, Any]:
        """Return paginated blocks with optional filtering."""

        limit = query.limit if query.limit is not None else self._default_limit
        offset = query.offset if query.offset is not None else 0
        items = self._repository.list(limit=limit, offset=offset)

        # Filters not supported at the repository level yet -> apply in python.
        items = self._apply_filters(items, query)

        return {
            "items": items[:limit],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
            },
        }

    def get_block(self, block_id: str) -> Dict[str, Any]:
        """Return a specific block or raise ``BlockNotFoundError``."""

        block = self._repository.get(block_id)
        if not block:
            raise BlockNotFoundError(block_id)
        return block

    def create_block(self, payload: BlockCreateSchema) -> Dict[str, Any]:
        """Create a new block."""

        prepared = payload.model_dump()
        parent_id = prepared.pop("parent_id", None)
        relation_type = prepared.pop("relation_type", "contains")

        try:
            block = self._repository.create(
                {**prepared, "relation_type": relation_type},
                parent_id=parent_id,
            )
        except RuntimeError as exc:
            raise BlockConflictError(str(exc)) from exc

        return block

    def update_block(self, block_id: str, payload: BlockUpdateSchema) -> Dict[str, Any]:
        """Update existing block properties."""

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_block(block_id)

        block = self._repository.update(block_id, updates)
        if not block:
            raise BlockNotFoundError(block_id)

        return block

    def delete_block(self, block_id: str) -> None:
        """Remove the block by its identifier."""

        deleted = self._repository.delete(block_id)
        if not deleted:
            raise BlockNotFoundError(block_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _apply_filters(self, items: List[Dict[str, Any]], params: BlockQuerySchema) -> List[Dict[str, Any]]:
        filtered = items
        if params.type:
            filtered = [item for item in filtered if item["properties"].get("type") == params.type]
        if params.search:
            needle = params.search.lower()
            filtered = [
                item
                for item in filtered
                if needle in (item["properties"].get("name", "").lower())
                or needle in (item["properties"].get("description", "").lower())
            ]
        return filtered

