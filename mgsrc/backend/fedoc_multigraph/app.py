"""Application factory for the multigraph backend."""
from __future__ import annotations

from flask import Flask

from .api import register_api
from .config.settings import Settings
from .errors import register_error_handlers
from .db import init_app as init_db
from .middleware import register_middlewares
from .realtime import graph_hub


def create_app() -> Flask:
    """Construct and configure the Flask application instance."""

    settings = Settings.from_env()

    app = Flask(__name__)
    app.config.from_mapping(settings.to_flask_config())
    app.config["FEDOC_SETTINGS"] = settings

    register_middlewares(app)
    register_error_handlers(app)
    init_db(app, settings.database_url)
    register_api(app)
    graph_hub.init_app(app)

    return app
