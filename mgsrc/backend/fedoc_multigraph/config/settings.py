"""Configuration handling for the multigraph backend."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Settings:
    """Service settings loaded from environment variables."""

    database_url: str = "postgresql://fedoc:fedoc@localhost:5432/fedoc_mg"
    graph_blocks_name: str = "mg_blocks"
    graph_designs_name: str = "mg_designs"
    api_default_limit: int = 50
    env: str = os.getenv("FEDOC_ENV", "development")
    debug: bool = os.getenv("FEDOC_DEBUG", "false").lower() == "true"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings instance from environment variables."""

        database_url = os.getenv("FEDOC_DATABASE_URL", cls.database_url)
        graph_blocks_name = os.getenv("FEDOC_GRAPH_BLOCKS", cls.graph_blocks_name)
        graph_designs_name = os.getenv("FEDOC_GRAPH_DESIGNS", cls.graph_designs_name)
        api_default_limit = int(os.getenv("FEDOC_API_DEFAULT_LIMIT", cls.api_default_limit))
        env = os.getenv("FEDOC_ENV", cls.env)
        debug = os.getenv("FEDOC_DEBUG", "false").lower() == "true"
        return cls(
            database_url=database_url,
            graph_blocks_name=graph_blocks_name,
            graph_designs_name=graph_designs_name,
            api_default_limit=api_default_limit,
            env=env,
            debug=debug,
        )

    def to_flask_config(self) -> Dict[str, Any]:
        """Convert settings to a mapping compatible with ``Flask.config``."""

        return {
            "ENV": self.env,
            "DEBUG": self.debug,
            "FEDOC_DATABASE_URL": self.database_url,
            "FEDOC_GRAPH_BLOCKS": self.graph_blocks_name,
            "FEDOC_GRAPH_DESIGNS": self.graph_designs_name,
            "FEDOC_API_DEFAULT_LIMIT": self.api_default_limit,
        }
