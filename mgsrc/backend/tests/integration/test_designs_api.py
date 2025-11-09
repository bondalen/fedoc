from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest

from .utils import create_block, create_design, delete_block, delete_design


pytestmark = pytest.mark.integration


def test_designs_crud_flow(client):
    """Full CRUD flow for designs including optional block linkage."""

    block = create_block(client, description="Block for design link")
    block_id = block["id"]

    design = create_design(
        client,
        block_id=block_id,
        description="Integration test design",
        status="draft",
    )
    design_id = design["id"]

    try:
        assert design.get("block_id") == block_id
        assert design["properties"]["status"] == "draft"

        get_resp = client.get(f"/api/designs/{design_id}")
        assert get_resp.status_code == HTTPStatus.OK, get_resp.get_data(as_text=True)
        fetched_design = get_resp.get_json()
        assert fetched_design.get("block_id") == block_id

        patch_payload = {
            "status": "active",
            "block_id": None,
            "description": "Integration test design (updated)",
        }
        patch_resp = client.patch(f"/api/designs/{design_id}", json=patch_payload)
        assert patch_resp.status_code == HTTPStatus.OK, patch_resp.get_data(as_text=True)
        updated_design = patch_resp.get_json()
        assert updated_design["properties"]["status"] == "active"
        assert updated_design.get("block_id") is None
        assert updated_design["properties"]["description"] == patch_payload["description"]

        delete_resp = client.delete(f"/api/designs/{design_id}")
        assert delete_resp.status_code == HTTPStatus.NO_CONTENT, delete_resp.get_data(as_text=True)

        get_deleted = client.get(f"/api/designs/{design_id}")
        assert get_deleted.status_code == HTTPStatus.NOT_FOUND

    finally:
        delete_design(client, design_id)
        delete_block(client, block_id)


def test_designs_get_nonexistent_returns_404(client):
    resp = client.get("/api/designs/999999999999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_designs_create_invalid_status_returns_422(client):
    payload = {"name": "invalid-status-design", "status": "unsupported"}
    resp = client.post("/api/designs/", json=payload)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_designs_create_with_unknown_block_returns_409(client):
    payload = {
        "name": f"design-with-unknown-block-{uuid.uuid4().hex[:6]}",
        "block_id": "999999:999999",
    }
    resp = client.post("/api/designs/", json=payload)
    assert resp.status_code == HTTPStatus.CONFLICT

