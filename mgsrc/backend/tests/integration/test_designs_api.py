from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest


pytestmark = pytest.mark.integration


def test_designs_crud_flow(client):
    """Full CRUD flow for designs including optional block linkage."""

    # Ensure at least one block exists to link against.
    block_name = f"pytest-block-{uuid.uuid4().hex[:6]}"
    create_block_resp = client.post(
        "/api/blocks/",
        json={"name": block_name, "description": "Block for design link", "type": "concept"},
    )
    assert create_block_resp.status_code == HTTPStatus.CREATED, create_block_resp.get_data(as_text=True)
    created_block = create_block_resp.get_json()
    block_id = created_block["id"]

    design_name = f"pytest-design-{uuid.uuid4().hex[:6]}"
    create_design_payload = {
        "name": design_name,
        "description": "Integration test design",
        "status": "draft",
        "block_id": block_id,
    }

    design_id = None
    try:
        create_design_resp = client.post("/api/designs/", json=create_design_payload)
        assert create_design_resp.status_code == HTTPStatus.CREATED, create_design_resp.get_data(as_text=True)
        created_design = create_design_resp.get_json()
        design_id = created_design["id"]
        assert created_design.get("block_id") == block_id
        assert created_design["properties"]["status"] == "draft"

        get_resp = client.get(f"/api/designs/{design_id}")
        assert get_resp.status_code == HTTPStatus.OK, get_resp.get_data(as_text=True)
        fetched_design = get_resp.get_json()
        assert fetched_design["properties"]["name"] == design_name
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
        deleted_id = design_id
        design_id = None

        get_deleted = client.get(f"/api/designs/{deleted_id}")
        assert get_deleted.status_code == HTTPStatus.NOT_FOUND

    finally:
        if design_id is not None:
            client.delete(f"/api/designs/{design_id}")
        client.delete(f"/api/blocks/{block_id}")

