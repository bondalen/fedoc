from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any, Dict


def _unique_suffix(length: int = 6) -> str:
    return uuid.uuid4().hex[:length]


def create_block(client, **overrides: Any) -> Dict[str, Any]:
    payload = {
        "name": f"pytest-block-{_unique_suffix()}",
        "description": "Block created for integration testing.",
        "type": "concept",
        "metadata": {"created_by": "tests"},
    }
    payload.update(overrides)
    response = client.post("/api/blocks/", json=payload)
    assert response.status_code == HTTPStatus.CREATED, response.get_data(as_text=True)
    return response.get_json()


def delete_block(client, block_id: str) -> None:
    client.delete(f"/api/blocks/{block_id}")


def create_design(client, *, block_id: str | None = None, **overrides: Any) -> Dict[str, Any]:
    payload = {
        "name": f"pytest-design-{_unique_suffix()}",
        "description": "Design created for integration testing.",
        "status": "draft",
        "block_id": block_id,
    }
    payload.update(overrides)
    response = client.post("/api/designs/", json=payload)
    assert response.status_code == HTTPStatus.CREATED, response.get_data(as_text=True)
    return response.get_json()


def delete_design(client, design_id: str) -> None:
    client.delete(f"/api/designs/{design_id}")


def create_project(client, **overrides: Any) -> Dict[str, Any]:
    payload = {
        "name": f"pytest-project-{_unique_suffix()}",
        "description": "Project created for integration testing.",
    }
    payload.update(overrides)
    response = client.post("/api/projects/", json=payload)
    assert response.status_code == HTTPStatus.CREATED, response.get_data(as_text=True)
    return response.get_json()


def delete_project(client, project_id: int | str) -> None:
    client.delete(f"/api/projects/{project_id}")

