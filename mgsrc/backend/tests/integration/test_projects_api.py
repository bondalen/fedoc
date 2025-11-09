from __future__ import annotations

import os
from http import HTTPStatus

import pytest

from fedoc_multigraph.config.settings import Settings
from fedoc_multigraph.db.session import SessionManager

from .utils import (
    create_block,
    create_design,
    create_project,
    delete_block,
    delete_design,
    delete_project,
)

pytestmark = pytest.mark.integration


def _get_session_manager() -> SessionManager:
    dsn = os.getenv("FEDOC_DATABASE_URL") or Settings.from_env().database_url
    return SessionManager(dsn)


def test_projects_crud_flow(client):
    project = create_project(client, description="Test project")
    project_id = project["id"]

    try:
        list_resp = client.get("/api/projects/")
        assert list_resp.status_code == HTTPStatus.OK
        items = list_resp.get_json()["items"]
        assert any(item["id"] == project_id for item in items)

        get_resp = client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == HTTPStatus.OK
        assert get_resp.get_json()["name"] == project["name"]

        patch_resp = client.patch(
            f"/api/projects/{project_id}",
            json={"description": "Updated description"},
        )
        assert patch_resp.status_code == HTTPStatus.OK
        assert patch_resp.get_json()["description"] == "Updated description"

        delete_resp = client.delete(f"/api/projects/{project_id}")
        assert delete_resp.status_code == HTTPStatus.NO_CONTENT

        not_found_resp = client.get(f"/api/projects/{project_id}")
        assert not_found_resp.status_code == HTTPStatus.NOT_FOUND
    finally:
        delete_project(client, project_id)


def test_projects_duplicate_name_returns_conflict(client):
    first = create_project(client)
    try:
        dup_resp = client.post("/api/projects/", json={"name": first["name"]})
        assert dup_resp.status_code == HTTPStatus.CONFLICT
    finally:
        delete_project(client, first["id"])


def test_projects_get_nonexistent_returns_404(client):
    resp = client.get("/api/projects/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_projects_patch_nonexistent_returns_404(client):
    resp = client.patch("/api/projects/987654", json={"description": "ghost"})
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_projects_patch_duplicate_name_returns_conflict(client):
    first = create_project(client)
    second = create_project(client)
    try:
        conflict_resp = client.patch(f"/api/projects/{second['id']}", json={"name": first["name"]})
        assert conflict_resp.status_code == HTTPStatus.CONFLICT
    finally:
        delete_project(client, first["id"])
        delete_project(client, second["id"])


def test_projects_create_invalid_payload_returns_422(client):
    resp = client.post("/api/projects/", json={"description": "missing name"})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_projects_graph_returns_designs_blocks(client):
    block = create_block(client, description="Block for project graph", type="component")
    block_id = block["id"]

    design_ids: list[str] = []
    session_manager = _get_session_manager()
    edge_id = None
    try:
        for _ in range(2):
            design = create_design(
                client,
                block_id=block_id,
                description="Design for project graph test",
                status="active",
            )
            design_ids.append(design["id"])

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

        project = create_project(client, design_edge_ids=[edge_id])
        project_id = project["id"]

        try:
            graph_resp = client.get(f"/api/projects/{project_id}/graph")
            assert graph_resp.status_code == HTTPStatus.OK, graph_resp.get_data(as_text=True)
            payload = graph_resp.get_json()
            assert payload["project"]["name"] == project["name"]

            designs = payload["graph"]["designs"]
            design_ids_in_graph = {item["id"] for item in designs}
            assert set(design_ids).issubset(design_ids_in_graph)

            edges = payload["graph"]["design_edges"]
            assert any(edge["id"] == edge_id for edge in edges)

            blocks = payload["graph"]["blocks"]
            assert any(item["id"] == block_id for item in blocks)
        finally:
            delete_project(client, project_id)

    finally:
        for design_id in design_ids:
            delete_design(client, design_id)
        if edge_id:
            with session_manager.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM mg_designs.design_edge WHERE id = %s::graphid",
                    (edge_id,),
                )
        delete_block(client, block_id)


def test_projects_graph_handles_missing_edges(client):
    session_manager = _get_session_manager()
    block = create_block(client, description="Block for missing edge test", type="component")
    block_id = block["id"]

    design_ids: list[str] = []
    try:
        for _ in range(2):
            design = create_design(
                client,
                block_id=block_id,
                status="active",
            )
            design_ids.append(design["id"])

        project = create_project(client, name="EdgeMissing-test")
        project_id = project["id"]

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
            delete_project(client, project_id)
    finally:
        for design_id in design_ids:
            delete_design(client, design_id)
        delete_block(client, block_id)

