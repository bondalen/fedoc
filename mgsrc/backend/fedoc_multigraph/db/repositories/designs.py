"""Repository for managing design vertices inside mg_designs graph."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from psycopg2 import Error

from ..session import SessionManager

GRAPH_NAME = "mg_designs"


class DesignsRepository:
    """Data access layer for design_node vertices and related mappings."""

    def __init__(self, session_manager: SessionManager, *, settings: Optional[Mapping[str, Any] | Any] = None) -> None:
        self._session_manager = session_manager
        if settings is None:
            self._graph_name = GRAPH_NAME
        else:
            self._graph_name = (
                getattr(settings, "graph_designs_name", None)
                or getattr(settings, "graph_name", None)
                or (settings.get("graph_name") if isinstance(settings, Mapping) else None)
                or GRAPH_NAME
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def list(self, *, limit: int, offset: int) -> List[Dict[str, Any]]:
        query = f"""
MATCH (d:design_node)
RETURN d
ORDER BY id(d)
SKIP {offset}
LIMIT {limit}
"""
        rows = self._run_cypher(query)
        items = [self._normalise_vertex(row) for row in rows]
        self._attach_block_links(items)
        return items

    def get(self, design_id: str) -> Dict[str, Any] | None:
        query = f"""
MATCH (d:design_node)
WHERE id(d) = {design_id}::graphid
RETURN d
"""
        rows = self._run_cypher(query)
        if not rows:
            return None
        design = self._normalise_vertex(rows[0])
        self._attach_block_links([design])
        return design

    def create(self, properties: Mapping[str, Any], *, block_id: Optional[str] = None) -> Dict[str, Any]:
        props = self._vertex_properties(properties)
        props_entries = self._map_entries(props)

        query = f"""
CREATE (d:design_node {{{props_entries}}})
RETURN d
"""
        rows = self._run_cypher(query)
        if not rows:
            raise RuntimeError("Failed to create design.")
        design = self._normalise_vertex(rows[0])

        if block_id:
            self._upsert_block_link(design["id"], block_id)
            design["block_id"] = block_id
        else:
            design["block_id"] = None
        return design

    def update(
        self,
        design_id: str,
        properties: Mapping[str, Any],
        *,
        block_id: object = None,
        block_id_provided: bool = False,
    ) -> Dict[str, Any]:
        props = self._vertex_properties(properties)

        if props:
            props_map = self._map_literal(props)
            query = f"""
MATCH (d:design_node)
WHERE id(d) = {design_id}::graphid
SET d += {props_map}
RETURN d
"""
            rows = self._run_cypher(query)
            if not rows:
                return {}
        else:
            rows = self._run_cypher(
                f"""
MATCH (d:design_node)
WHERE id(d) = {design_id}::graphid
RETURN d
"""
            )
            if not rows:
                return {}

        if block_id_provided:
            if block_id is None:
                self._delete_block_link(design_id)
            else:
                self._upsert_block_link(design_id, block_id)  # type: ignore[arg-type]

        design = self._normalise_vertex(rows[0])
        self._attach_block_links([design])
        return design

    def delete(self, design_id: str) -> bool:
        existing = self.get(design_id)
        if not existing:
            return False

        self._delete_block_link(design_id)

        delete_query = f"""
MATCH (d:design_node)
WHERE id(d) = {design_id}::graphid
DETACH DELETE d
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

    def _attach_block_links(self, items: List[Dict[str, Any]]) -> None:
        design_ids = [item["id"] for item in items if item.get("id")]
        if not design_ids:
            return

        query = """
SELECT design_id::text AS design_id, block_id::text AS block_id
FROM mg.design_to_block
WHERE design_id::text = ANY(%s)
"""
        with self._session_manager.cursor() as cursor:
            cursor.execute(query, (design_ids,))
            mappings = {row["design_id"]: row["block_id"] for row in cursor.fetchall() if row.get("block_id")}

        for item in items:
            item["block_id"] = mappings.get(item["id"])

    def _upsert_block_link(self, design_id: str, block_id: str) -> None:
        query = """
INSERT INTO mg.design_to_block (design_id, block_id)
VALUES (%s::graphid, %s::graphid)
ON CONFLICT (design_id)
DO UPDATE SET block_id = EXCLUDED.block_id
"""
        try:
            with self._session_manager.cursor() as cursor:
                cursor.execute(query, (design_id, block_id))
        except Error as exc:  # pragma: no cover - converted to runtime error
            raise RuntimeError(str(exc)) from exc

    def _delete_block_link(self, design_id: str) -> None:
        query = "DELETE FROM mg.design_to_block WHERE design_id::text = %s"
        with self._session_manager.cursor() as cursor:
            cursor.execute(query, (design_id,))

    @staticmethod
    def _vertex_properties(properties: Mapping[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in properties.items() if key not in {"block_id"}}

    @staticmethod
    def _map_literal(payload: Mapping[str, Any]) -> str:
        return "{" + DesignsRepository._map_entries(payload) + "}"

    @staticmethod
    def _map_entries(payload: Mapping[str, Any]) -> str:
        items = ", ".join(
            f"{key}: {DesignsRepository._cypher_value(value)}" for key, value in payload.items()
        )
        return items

    @staticmethod
    def _escape_cypher_string(value: str) -> str:
        return value.replace("'", "\\'")

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
            return DesignsRepository._map_literal(value)
        if isinstance(value, (list, tuple)):
            inner = ", ".join(DesignsRepository._cypher_value(item) for item in value)
            return "[" + inner + "]"
        if isinstance(value, datetime):
            return f"'{value.isoformat()}'"
        escaped = json.dumps(value, ensure_ascii=False).replace("'", "\\'")
        return f"'{escaped}'"

    @staticmethod
    def _normalise_vertex(payload: Mapping[str, Any]) -> Dict[str, Any]:
        vertex_id = payload.get("id")
        id_str = DesignsRepository._stringify_graphid(vertex_id)
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

