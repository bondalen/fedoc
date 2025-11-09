"""Business logic for project management."""
from __future__ import annotations

from typing import Any, Dict, List

from ..db.repositories.blocks import BlocksRepository
from ..db.repositories.designs import DesignsRepository
from ..db.repositories.projects import ProjectsRepository
from ..errors.projects import ProjectConflictError, ProjectNotFoundError
from ..validators.projects import ProjectCreateSchema, ProjectQuerySchema, ProjectUpdateSchema


class _Unset:
    pass


UNSET = _Unset()


class ProjectsService:
    """Encapsulates business logic for projects."""

    def __init__(
        self,
        repository: ProjectsRepository,
        designs_repo: DesignsRepository,
        blocks_repo: BlocksRepository,
        *,
        default_limit: int = 50,
    ) -> None:
        self._repository = repository
        self._designs_repo = designs_repo
        self._blocks_repo = blocks_repo
        self._default_limit = default_limit

    def list_projects(self, query: ProjectQuerySchema) -> Dict[str, Any]:
        limit = query.limit if query.limit is not None else self._default_limit
        offset = query.offset if query.offset is not None else 0
        projects = self._repository.list(limit=limit, offset=offset, search=query.search)
        return {
            "items": projects[:limit],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(projects),
            },
        }

    def get_project(self, project_id: int) -> Dict[str, Any]:
        project = self._repository.get(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        project["design_edge_ids"] = self._repository.get_design_edge_ids(project_id)
        return project

    def create_project(self, payload: ProjectCreateSchema) -> Dict[str, Any]:
        data = payload.model_dump()
        design_edge_ids = data.pop("design_edge_ids", None) or []
        try:
            project = self._repository.create(data)
        except RuntimeError as exc:
            raise ProjectConflictError(str(exc)) from exc
        if design_edge_ids:
            self._repository.set_design_edge_ids(project["id"], design_edge_ids)
        project["design_edge_ids"] = design_edge_ids
        return project

    def update_project(self, project_id: int, payload: ProjectUpdateSchema) -> Dict[str, Any]:
        updates = payload.model_dump(exclude_unset=True)
        design_edge_ids = updates.pop("design_edge_ids", UNSET)
        try:
            project = self._repository.update(project_id, updates)
        except RuntimeError as exc:
            raise ProjectConflictError(str(exc)) from exc
        if not project:
            raise ProjectNotFoundError(project_id)
        if design_edge_ids is not UNSET:
            ids = design_edge_ids or []
            self._repository.set_design_edge_ids(project_id, ids)
        project["design_edge_ids"] = self._repository.get_design_edge_ids(project_id)
        return project

    def delete_project(self, project_id: int) -> None:
        deleted = self._repository.delete(project_id)
        if not deleted:
            raise ProjectNotFoundError(project_id)

    def get_project_graph(self, project_id: int) -> Dict[str, Any]:
        project = self.get_project(project_id)
        edge_ids = project["design_edge_ids"]
        edges_payload = self._repository.fetch_design_edge_details(edge_ids)

        design_map: Dict[str, Dict[str, Any]] = {}
        for entry in edges_payload:
            for key in ("source_id", "target_id"):
                design_id = entry.get(key)
                if not design_id:
                    continue
                design = self._designs_repo.get(design_id)
                if not design:
                    design = {
                        "id": design_id,
                        "label": "design_node",
                        "properties": {},
                        "block_id": None,
                    }
                design_map[design_id] = design

        block_ids = {design.get("block_id") for design in design_map.values()} - {None}
        blocks = []
        for block_id in block_ids:
            block = self._blocks_repo.get(block_id) if block_id else None
            if block:
                blocks.append(block)

        edges = []
        for entry in edges_payload:
            edge_raw = entry["edge"]
            edge = self._normalise_edge(edge_raw)
            edges.append(edge)

        return {
            "project": project,
            "graph": {
                "designs": list(design_map.values()),
                "design_edges": edges,
                "blocks": blocks,
            },
        }

    @staticmethod
    def _normalise_edge(edge_payload: Mapping[str, Any]) -> Dict[str, Any]:
        edge_id = edge_payload.get("id")
        edge_str = ProjectsService._stringify_graphid(edge_id)
        return {
            "id": edge_str,
            "label": edge_payload.get("label"),
            "properties": edge_payload.get("properties", {}),
            "start_id": ProjectsService._stringify_graphid(edge_payload.get("start_id")),
            "end_id": ProjectsService._stringify_graphid(edge_payload.get("end_id")),
        }

    @staticmethod
    def _stringify_graphid(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            if "graphid" in value:
                return str(value["graphid"])
            graph_oid = value.get("graph_oid") or value.get("oid") or value.get("graph")
            local_id = value.get("id")
            if graph_oid is not None and local_id is not None:
                return f"{graph_oid}:{local_id}"
        return str(value)

