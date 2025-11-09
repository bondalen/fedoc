"""Repository for managing projects stored in relational tables."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

from psycopg2 import IntegrityError

from ..session import SessionManager


class ProjectsRepository:
    """Data access layer for mg.projects and mg.design_edge_to_project."""

    def __init__(self, session_manager: SessionManager, *, settings: Optional[Mapping[str, Any] | Any] = None) -> None:
        self._session_manager = session_manager
        if settings is None:
            self._design_graph = "mg_designs"
        else:
            self._design_graph = getattr(settings, "graph_designs_name", None) or getattr(settings, "graph_name", None) or (
                settings.get("graph_name") if isinstance(settings, Mapping) else None
            ) or "mg_designs"

    # ------------------------------------------------------------------ #
    # Projects table
    # ------------------------------------------------------------------ #
    def list(self, *, limit: int, offset: int, search: Optional[str] = None) -> List[Dict[str, Any]]:
        query = [
            "SELECT id, name, description, created_at",
            "FROM mg.projects",
        ]
        params: List[Any] = []
        if search:
            query.append("WHERE name ILIKE %s")
            params.append(f"%{search}%")
        query.append("ORDER BY created_at DESC")
        query.append("LIMIT %s OFFSET %s")
        params.extend([limit, offset])

        with self._session_manager.cursor() as cursor:
            cursor.execute(" ".join(query), params)
            rows = cursor.fetchall()

        return [self._normalise_project(row) for row in rows]

    def get(self, project_id: int) -> Dict[str, Any] | None:
        with self._session_manager.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, created_at FROM mg.projects WHERE id = %s",
                (project_id,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return self._normalise_project(row)

    def create(self, properties: Mapping[str, Any]) -> Dict[str, Any]:
        with self._session_manager.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO mg.projects (name, description) VALUES (%s, %s) "
                    "RETURNING id, name, description, created_at",
                    (properties.get("name"), properties.get("description")),
                )
            except IntegrityError as exc:  # pragma: no cover - raised to caller
                raise RuntimeError(str(exc)) from exc
            row = cursor.fetchone()
        return self._normalise_project(row)

    def update(self, project_id: int, properties: Mapping[str, Any]) -> Dict[str, Any]:
        if not properties:
            return self.get(project_id) or {}

        columns = []
        params: List[Any] = []
        if "name" in properties and properties["name"] is not None:
            columns.append("name = %s")
            params.append(properties["name"])
        if "description" in properties:
            columns.append("description = %s")
            params.append(properties["description"])

        if not columns:
            return self.get(project_id) or {}

        params.append(project_id)
        with self._session_manager.cursor() as cursor:
            try:
                cursor.execute(
                    "UPDATE mg.projects SET " + ", ".join(columns) + " WHERE id = %s "
                    "RETURNING id, name, description, created_at",
                    params,
                )
            except IntegrityError as exc:  # pragma: no cover
                raise RuntimeError(str(exc)) from exc
            row = cursor.fetchone()
        if not row:
            return {}
        return self._normalise_project(row)

    def delete(self, project_id: int) -> bool:
        with self._session_manager.cursor() as cursor:
            cursor.execute("DELETE FROM mg.design_edge_to_project WHERE project_id = %s", (project_id,))
            cursor.execute("DELETE FROM mg.projects WHERE id = %s RETURNING id", (project_id,))
            deleted = cursor.fetchone() is not None
        return deleted

    # ------------------------------------------------------------------ #
    # Project ↔ design edges mapping
    # ------------------------------------------------------------------ #
    def get_design_edge_ids(self, project_id: int) -> List[str]:
        with self._session_manager.cursor() as cursor:
            cursor.execute(
                "SELECT edge_id::text AS edge_id FROM mg.design_edge_to_project WHERE project_id = %s",
                (project_id,),
            )
            rows = cursor.fetchall()
        return [row["edge_id"] for row in rows if row.get("edge_id")]

    def set_design_edge_ids(self, project_id: int, edge_ids: Sequence[str]) -> None:
        with self._session_manager.cursor() as cursor:
            cursor.execute("DELETE FROM mg.design_edge_to_project WHERE project_id = %s", (project_id,))
            if edge_ids:
                values = [(edge_id, project_id) for edge_id in edge_ids]
                cursor.executemany(
                    "INSERT INTO mg.design_edge_to_project (edge_id, project_id) VALUES (%s::graphid, %s)",
                    values,
                )

    def fetch_design_edge_details(self, edge_ids: Sequence[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for edge_id in edge_ids:
            with self._session_manager.cursor() as cursor:
                cursor.execute(
                    "SELECT "
                    " id::text AS edge_id, "
                    " start_id::text AS start_id, "
                    " end_id::text AS end_id, "
                    " ag_catalog.agtype_to_json(properties) AS properties "
                    "FROM mg_designs.design_edge "
                    "WHERE id = %s::graphid",
                    (edge_id,),
                )
                row = cursor.fetchone()
            if not row:
                continue
            edge_properties = self._parse_agtype(row.get("properties")) or {}
            results.append(
                {
                    "edge": {
                        "id": row["edge_id"],
                        "label": "design_edge",
                        "properties": edge_properties,
                        "start_id": row["start_id"],
                        "end_id": row["end_id"],
                    },
                    "source_id": row["start_id"],
                    "target_id": row["end_id"],
                }
            )
        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_project(row: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row.get("description"),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        }

    @staticmethod
    def _parse_agtype(value: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if isinstance(value, memoryview):
            value = value.tobytes().decode()
        if isinstance(value, bytes):
            value = value.decode()
        if isinstance(value, str):
            return json.loads(value)
        return value

