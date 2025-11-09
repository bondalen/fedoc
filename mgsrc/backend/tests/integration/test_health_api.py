from __future__ import annotations

from http import HTTPStatus

import pytest

pytestmark = pytest.mark.integration


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json() == {"status": "ok"}

