from __future__ import annotations

import json
import os
import uuid
from http import HTTPStatus

import pytest

from fedoc_multigraph.config.settings import Settings
from fedoc_multigraph.db.session import SessionManager

pytestmark = pytest.mark.integration


def _get_session_manager() -> SessionManager:
    dsn = os.getenv("FEDOC_DATABASE_URL") or Settings.from_env().database_url
    return SessionManager(dsn)


def test_projects_crud_flow(client):
    unique_name = f"Project-{uuid.uuid4().hex[:6]}"
    create_resp = client.post("/api/projects/", json={"name": unique_name, "description": "Test project"})
    assert create_resp.status_code == HTTPStatus.CREATED, create_resp.get_data(as_text=True)
    created_project = create_resp.get_json()
    project_id = created_project["id"]

    try:
        list_resp = client.get("/api/projects/")
        assert list_resp.status_code == HTTPStatus.OK
        items = list_resp.get_json()["items"]
        assert any(item["id"] == project_id for item in items)

        get_resp = client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == HTTPStatus.OK
        assert get_resp.get_json()["name"] == unique_name

        patch_resp = client.patch(
            f"/api/projects/{project_id}",
            json={"description": "Updated description"},
        )
        assert patch_resp.status_code == HTTPStatus.OK
        assert patch_resp.get_json()["description"] == "Updated description"

        delete_resp = client.delete(f"/api/projects/{project_id}")
        assert delete_resp.status_code == HTTPStatus.NO_CONTENT
        project_id = None

        not_found_resp = client.get(f"/api/projects/{created_project['id']}")
        assert not_found_resp.status_code == HTTPStatus.NOT_FOUND
    finally:
        if project_id is not None:
            client.delete(f"/api/projects/{project_id}")


def test_projects_duplicate_name_returns_conflict(client):
    name = f"Duplicate-{uuid.uuid4().hex[:6]}"
    first = client.post("/api/projects/", json={"name": name})
    assert first.status_code == HTTPStatus.CREATED
    project_id = first.get_json()["id"]
    try:
        second = client.post("/api/projects/", json={"name": name})
        assert second.status_code == HTTPStatus.CONFLICT
    finally:
        client.delete(f"/api/projects/{project_id}")


def test_projects_graph_returns_designs_blocks(client):
    block_resp = client.post(
        "/api/blocks/",
        json={
            "name": f"ProjBlock-{uuid.uuid4().hex[:6]}",
            "description": "Block for project graph",
            "type": "component",
        },
    )
    assert block_resp.status_code == HTTPStatus.CREATED
    block = block_resp.get_json()
    block_id = block["id"]

    design_ids = []
    try:
        for suffix in ("A", "B"):
            design_resp = client.post(
                "/api/designs/",
                json={
                    "name": f"ProjectDesign-{suffix}-{uuid.uuid4().hex[:4]}",
                    "description": "Design for project graph test",
                    "status": "active",
                    "block_id": block_id,
                },
            )
            assert design_resp.status_code == HTTPStatus.CREATED
            design_ids.append(design_resp.get_json()["id"])

        # Create design edge between the two designs.
        session_manager = _get_session_manager()
        edge_id = None
        with session_manager.cursor() as cursor:
            cursor.execute(
                "INSERT INTO mg_designs.design_edge (start_id, end_id, properties) "
                "VALUES (%s::graphid, %s::graphid, %s::agtype) "
                "RETURNING id::text;",
                (
                    design_ids[0],
                    design_ids[1],
                    '{"relation_type": "references"}',
                ),
            )
            edge_row = cursor.fetchone()
        edge_id = edge_row["id"] if edge_row else None

        assert edge_id, "Design edge should be created."

        project_name = f"GraphProject-{uuid.uuid4().hex[:6]}"
        create_project = client.post(
            "/api/projects/",
            json={"name": project_name, "design_edge_ids": [edge_id]},
        )
        assert create_project.status_code == HTTPStatus.CREATED
        project_id = create_project.get_json()["id"]

        try:
            graph_resp = client.get(f"/api/projects/{project_id}/graph")
            assert graph_resp.status_code == HTTPStatus.OK, graph_resp.get_data(as_text=True)
            payload = graph_resp.get_json()
            assert payload["project"]["name"] == project_name

            designs = payload["graph"]["designs"]
            design_ids_in_graph = {item["id"] for item in designs}
            assert set(design_ids).issubset(design_ids_in_graph)

            edges = payload["graph"]["design_edges"]
            assert any(edge["id"] == edge_id for edge in edges)

            blocks = payload["graph"]["blocks"]
            assert any(item["id"] == block_id for item in blocks)
        finally:
            client.delete(f"/api/projects/{project_id}")

    finally:
        for design_id in design_ids:
            client.delete(f"/api/designs/{design_id}")
        if edge_id:
            with session_manager.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM mg_designs.design_edge WHERE id = %s::graphid",
                    (edge_id,),
                )
        client.delete(f"/api/blocks/{block_id}")

