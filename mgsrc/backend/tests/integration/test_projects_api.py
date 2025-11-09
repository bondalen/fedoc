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


def test_projects_get_nonexistent_returns_404(client):
    resp = client.get("/api/projects/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_projects_patch_nonexistent_returns_404(client):
    resp = client.patch("/api/projects/987654", json={"description": "ghost"})
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_projects_patch_duplicate_name_returns_conflict(client):
    first_name = f"Primary-{uuid.uuid4().hex[:6]}"
    second_name = f"Secondary-{uuid.uuid4().hex[:6]}"

    first_resp = client.post("/api/projects/", json={"name": first_name})
    assert first_resp.status_code == HTTPStatus.CREATED
    first_id = first_resp.get_json()["id"]

    second_resp = client.post("/api/projects/", json={"name": second_name})
    assert second_resp.status_code == HTTPStatus.CREATED
    second_id = second_resp.get_json()["id"]

    try:
        conflict_resp = client.patch(f"/api/projects/{second_id}", json={"name": first_name})
        assert conflict_resp.status_code == HTTPStatus.CONFLICT
    finally:
        client.delete(f"/api/projects/{first_id}")
        client.delete(f"/api/projects/{second_id}")


def test_projects_create_invalid_payload_returns_422(client):
    resp = client.post("/api/projects/", json={"description": "missing name"})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


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


def test_projects_graph_handles_missing_edges(client):
    session_manager = _get_session_manager()
    block_resp = client.post(
        "/api/blocks/",
        json={
            "name": f"MissingEdgeBlock-{uuid.uuid4().hex[:6]}",
            "description": "Block for missing edge test",
            "type": "component",
        },
    )
    assert block_resp.status_code == HTTPStatus.CREATED
    block_id = block_resp.get_json()["id"]

    design_ids = []
    try:
        for suffix in ("X", "Y"):
            design_resp = client.post(
                "/api/designs/",
                json={
                    "name": f"MissingEdgeDesign-{suffix}-{uuid.uuid4().hex[:4]}",
                    "status": "active",
                    "block_id": block_id,
                },
            )
            assert design_resp.status_code == HTTPStatus.CREATED
            design_ids.append(design_resp.get_json()["id"])

        project_resp = client.post("/api/projects/", json={"name": f"EdgeMissing-{uuid.uuid4().hex[:6]}"})
        assert project_resp.status_code == HTTPStatus.CREATED
        project_id = project_resp.get_json()["id"]

        try:
            with session_manager.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mg_designs.design_edge (start_id, end_id, properties) "
                    "VALUES (%s::graphid, %s::graphid, %s::agtype) "
                    "RETURNING id::text AS edge_id",
                    (
                        design_ids[0],
                        design_ids[1],
                        '{"relation_type": "temporary"}',
                    ),
                )
                row = cursor.fetchone()
            edge_id = row["edge_id"] if row else None
            assert edge_id

            assign_resp = client.patch(
                f"/api/projects/{project_id}",
                json={"design_edge_ids": [edge_id]},
            )
            assert assign_resp.status_code == HTTPStatus.OK

            with session_manager.cursor() as cursor:
                cursor.execute("DELETE FROM mg_designs.design_edge WHERE id = %s::graphid", (edge_id,))

            graph_resp = client.get(f"/api/projects/{project_id}/graph")
            assert graph_resp.status_code == HTTPStatus.OK
            payload = graph_resp.get_json()
            assert payload["graph"]["design_edges"] == []
            assert payload["graph"]["designs"] == []
        finally:
            client.delete(f"/api/projects/{project_id}")
    finally:
        for design_id in design_ids:
            client.delete(f"/api/designs/{design_id}")
        client.delete(f"/api/blocks/{block_id}")

