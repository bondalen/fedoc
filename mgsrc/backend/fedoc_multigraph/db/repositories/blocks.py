"""Repository for managing block vertices inside mg_blocks graph."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from ..session import SessionManager

GRAPH_NAME = "mg_blocks"


class BlocksRepository:
    """Data access layer for block_type vertices and block_edge relations."""

    def __init__(self, session_manager: SessionManager, *, settings: Optional[Mapping[str, Any] | Any] = None) -> None:
        self._session_manager = session_manager
        if settings is None:
            self._graph_name = GRAPH_NAME
        else:
            self._graph_name = getattr(settings, "graph_blocks_name", None) or getattr(settings, "graph_name", None) or (
                settings.get("graph_name") if isinstance(settings, Mapping) else None
            ) or GRAPH_NAME

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def list(self, *, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Return a page of blocks."""

        query = f"""
MATCH (b:block_type)
RETURN b
ORDER BY id(b)
SKIP {offset}
LIMIT {limit}
"""
        rows = self._run_cypher(query)
        return [self._normalise_vertex(row) for row in rows]

    def get(self, block_id: str) -> Dict[str, Any] | None:
        """Return a block by its graph id."""

        query = f"""
MATCH (b:block_type)
WHERE id(b) = {block_id}::graphid
RETURN b
"""
        rows = self._run_cypher(query)
        if not rows:
            return None
        return self._normalise_vertex(rows[0])

    def create(self, properties: Mapping[str, Any], *, parent_id: str | None = None) -> Dict[str, Any]:
        """Create a block vertex and optional relation to a parent."""

        props = self._vertex_properties(properties)
        relation_type = properties.get("relation_type", "contains")

        props_entries = self._map_entries(props)

        if parent_id:
            query = f"""
MATCH (parent:block_type)
WHERE id(parent) = {parent_id}::graphid
CREATE (child:block_type {{{props_entries}}})
CREATE (parent)-[:block_edge {{relation_type: '{self._escape_cypher_string(relation_type)}'}}]->(child)
RETURN child
"""
        else:
            query = f"""
CREATE (child:block_type {{{props_entries}}})
RETURN child
"""

        rows = self._run_cypher(query)
        if not rows:
            raise RuntimeError("Failed to create block.")
        return self._normalise_vertex(rows[0])

    def update(self, block_id: str, properties: Mapping[str, Any]) -> Dict[str, Any]:
        """Update mutable properties of a block."""

        props = self._vertex_properties(properties)
        if not props:
            query = f"""
MATCH (child:block_type)
WHERE id(child) = {block_id}::graphid
RETURN child
"""
            rows = self._run_cypher(query)
            if not rows:
                return {}
            return self._normalise_vertex(rows[0])

        props_map = self._map_literal(props)
        query = f"""
MATCH (child:block_type)
WHERE id(child) = {block_id}::graphid
SET child += {props_map}
RETURN child
"""
        rows = self._run_cypher(query)
        if not rows:
            return {}
        return self._normalise_vertex(rows[0])

    def delete(self, block_id: str) -> bool:
        """Remove a block and its relations."""

        # First check if block exists
        check_query = f"""
MATCH (child:block_type)
WHERE id(child) = {block_id}::graphid
RETURN child
"""
        existing = self._run_cypher(check_query)
        if not existing:
            return False
            
        # Then delete it
        delete_query = f"""
MATCH (child:block_type)
WHERE id(child) = {block_id}::graphid
DETACH DELETE child
"""
        self._run_cypher(delete_query)
        return True

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _run_cypher(self, query: str) -> List[Dict[str, Any]]:
        with self._session_manager.cursor() as cursor:
            graph_literal = cursor.mogrify("%s", (self._graph_name,))
            delimiter = "mg"
            while f"${delimiter}$" in query:
                delimiter += "_x"
            body = f"${delimiter}${query}${delimiter}$".encode("utf-8")

            sql_bytes = (
                b"SELECT ag_catalog.agtype_to_json(result) AS result "
                b"FROM ag_catalog.cypher("
                + graph_literal
                + b", "
                + body
                + b") AS (result agtype)"
            )

            cursor.execute(sql_bytes)
            rows = cursor.fetchall()

        return [row["result"] for row in rows]

    @staticmethod
    def _raw_value(value: Any) -> str:
        if isinstance(value, memoryview):
            return value.tobytes().decode()
        if isinstance(value, bytes):
            return value.decode()
        return str(value)

    @staticmethod
    def _vertex_properties(properties: Mapping[str, Any]) -> Dict[str, Any]:
        filtered: Dict[str, Any] = {}
        for key, value in properties.items():
            if key in {"relation_type", "parent_id"}:
                continue
            if key == "metadata" and isinstance(value, Mapping) and not value:
                continue
            filtered[key] = value
        return filtered

    @staticmethod
    def _map_literal(payload: Mapping[str, Any]) -> str:
        return "{" + BlocksRepository._map_entries(payload) + "}"

    @staticmethod
    def _map_entries(payload: Mapping[str, Any]) -> str:
        items = ", ".join(
            f"{key}: {BlocksRepository._cypher_value(value)}" for key, value in payload.items()
        )
        return items

    @staticmethod
    def _escape_cypher_string(value: str) -> str:
        return value.replace("'", "\\'")

    @staticmethod
    def _quote_literal(value: str) -> str:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    @staticmethod
    def _cypher_value(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
        if isinstance(value, Mapping):
            return BlocksRepository._map_literal(value)
        if isinstance(value, (list, tuple)):
            inner = ", ".join(BlocksRepository._cypher_value(item) for item in value)
            return "[" + inner + "]"
        # Fallback: use JSON representation as string
        escaped = json.dumps(value, ensure_ascii=False).replace("'", "\\'")
        return f"'{escaped}'"

    @staticmethod
    def _normalise_vertex(payload: Mapping[str, Any]) -> Dict[str, Any]:
        vertex_id = payload.get("id")
        id_str = BlocksRepository._stringify_graphid(vertex_id)
        
        # Extract graph name from vertex_id if it's a dict, otherwise from payload
        graph_name = None
        if isinstance(vertex_id, Mapping):
            graph_name = (
                vertex_id.get("graph")
                or vertex_id.get("graph_name")
                or vertex_id.get("graph_oid")
            )
        if not graph_name:
            graph_name = payload.get("graph")
            
        return {
            "id": id_str,
            "graph": graph_name,
            "raw_id": vertex_id,
            "label": payload.get("label"),
            "properties": payload.get("properties", {}),
        }

    @staticmethod
    def _stringify_graphid(vertex_id: Any) -> str:
        if isinstance(vertex_id, str):
            return vertex_id
        if isinstance(vertex_id, Mapping):
            if "graphid" in vertex_id:
                return str(vertex_id["graphid"])
            graph_oid = vertex_id.get("graph_oid") or vertex_id.get("oid") or vertex_id.get("graph")
            local_id = vertex_id.get("id")
            if graph_oid is not None and local_id is not None:
                return f"{graph_oid}:{local_id}"
        return str(vertex_id)

