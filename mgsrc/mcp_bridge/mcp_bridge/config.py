"""Configuration helpers for the MCP Bridge."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BridgeConfig:
    """Runtime configuration for the MCP Bridge."""

    websocket_url: str = os.getenv("FEDOC_WS_URL", "ws://localhost:8080/ws")
    reconnect_delay: float = float(os.getenv("FEDOC_WS_RECONNECT_DELAY", "5.0"))
    selection_channel: str = os.getenv("FEDOC_WS_SELECTION_CHANNEL", "selection_updates")
    graph_channel: str = os.getenv("FEDOC_WS_GRAPH_CHANNEL", "graph_updates")
    client_origin: str = os.getenv("FEDOC_MCP_ORIGIN", "mcp")

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Read configuration from environment variables."""

        return cls()

