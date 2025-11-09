from __future__ import annotations

import os
import pytest

from fedoc_multigraph.app import create_app


@pytest.fixture(scope="session")
def app():
    """Return configured Flask application for tests or skip if DB is unavailable."""

    if not os.getenv("FEDOC_DATABASE_URL"):
        pytest.skip("FEDOC_DATABASE_URL environment variable is not set.")
    return create_app()


@pytest.fixture
def client(app):
    """Provide Flask test client with active application context."""

    with app.app_context():
        with app.test_client() as test_client:
            yield test_client

