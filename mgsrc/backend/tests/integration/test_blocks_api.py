from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest


pytestmark = pytest.mark.integration


def _extract_items(response_json: dict) -> list[dict]:
    items = response_json.get("items")
    assert isinstance(items, list), "Expected 'items' to be a list"
    return items


def test_blocks_crud_flow(client):
    """Ensure full CRUD cycle for blocks works against the configured database."""

    list_resp = client.get("/api/blocks/")
    assert list_resp.status_code == HTTPStatus.OK, list_resp.get_data(as_text=True)
    initial_payload = list_resp.get_json()
    initial_items = _extract_items(initial_payload)
    initial_count = initial_payload.get("pagination", {}).get("count", len(initial_items))

    block_id = None
    unique_suffix = uuid.uuid4().hex[:8]
    create_payload = {
        "name": f"pytest-block-{unique_suffix}",
        "description": "Integration test block",
        "type": "concept",
        "metadata": {"purpose": "integration-test", "marker": unique_suffix},
    }

    try:
        create_resp = client.post("/api/blocks/", json=create_payload)
        assert create_resp.status_code == HTTPStatus.CREATED, create_resp.get_data(as_text=True)
        created = create_resp.get_json()
        assert isinstance(created, dict)
        block_id = created.get("id")
        assert block_id, "API should return created block id"

        properties = created.get("properties", {})
        assert properties.get("name") == create_payload["name"]
        assert properties.get("metadata", {}).get("marker") == unique_suffix

        get_resp = client.get(f"/api/blocks/{block_id}")
        assert get_resp.status_code == HTTPStatus.OK, get_resp.get_data(as_text=True)
        fetched = get_resp.get_json()
        assert fetched.get("id") == block_id
        assert fetched.get("properties", {}).get("name") == create_payload["name"]

        patch_payload = {
            "description": "Integration test block (updated)",
            "metadata": {"purpose": "integration-test", "updated": True},
        }
        patch_resp = client.patch(f"/api/blocks/{block_id}", json=patch_payload)
        assert patch_resp.status_code == HTTPStatus.OK, patch_resp.get_data(as_text=True)
        updated = patch_resp.get_json()
        updated_props = updated.get("properties", {})
        assert updated_props.get("description") == patch_payload["description"]
        assert updated_props.get("metadata", {}).get("updated") is True

        delete_resp = client.delete(f"/api/blocks/{block_id}")
        assert delete_resp.status_code == HTTPStatus.NO_CONTENT, delete_resp.get_data(as_text=True)
        block_id = None  # Prevent double-cleanup in finally if deletion succeeded

    finally:
        if block_id:
            client.delete(f"/api/blocks/{block_id}")

    final_resp = client.get("/api/blocks/")
    assert final_resp.status_code == HTTPStatus.OK, final_resp.get_data(as_text=True)
    final_payload = final_resp.get_json()
    final_items = _extract_items(final_payload)
    assert create_payload["name"] not in {item.get("properties", {}).get("name") for item in final_items}

    final_count = final_payload.get("pagination", {}).get("count", len(final_items))
    assert final_count == initial_count
    assert len(final_items) == len(initial_items)


def test_blocks_get_nonexistent_returns_404(client):
    resp = client.get("/api/blocks/999999999999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_blocks_create_invalid_payload_returns_422(client):
    resp = client.post("/api/blocks/", json={"description": "Missing required fields"})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
