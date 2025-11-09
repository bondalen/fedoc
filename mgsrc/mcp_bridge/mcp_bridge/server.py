"""Core MCP Bridge server coordinating WebSocket and command handlers."""
from __future__ import annotations

import json
import logging
import os
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, Dict, Iterable, Optional

from .config import BridgeConfig
from .websocket_bridge import WebSocketBridge

LOGGER = logging.getLogger(__name__)


class MCPBridge:
    """Lightweight MCP-oriented interface on top of the WebSocket bridge."""

    def __init__(self, config: Optional[BridgeConfig] = None) -> None:
        self._config = config or BridgeConfig.from_env()
        self._ws = WebSocketBridge(self._config)
        self._ws.add_listener("hello", self._handle_hello)
        self._ws.add_listener("graph_updated", self._handle_graph_update)
        self._ws.add_listener("selected_nodes", self._handle_selection)
        self._ws.add_listener("error", self._handle_error)

        self._thread: Optional[Thread] = None
        self._graph_updates: Queue[Dict[str, Any]] = Queue()
        self._selection_snapshot: Optional[Dict[str, Any]] = None
        self._stop_event = Event()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Run the WebSocket bridge in a background thread."""

        if self._thread and self._thread.is_alive():
            LOGGER.debug("MCPBridge already running.")
            return

        LOGGER.info("Starting MCP Bridge (WebSocket URL: %s)", self._config.websocket_url)
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="mcp-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop bridge and worker thread."""

        LOGGER.info("Stopping MCP Bridge.")
        self._stop_event.set()
        self._ws.stop()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------ #
    # High-level operations exposed to MCP handlers
    # ------------------------------------------------------------------ #
    def push_selection(self, nodes: Iterable[str], edges: Iterable[str]) -> None:
        """Publish selection update to the backend hub."""

        self._ws.broadcast_selection(nodes, edges)

    def get_selection_snapshot(self) -> Optional[Dict[str, Any]]:
        """Return last known selection state."""

        return self._selection_snapshot

    def request_selection_refresh(self) -> None:
        """Ask the hub for current selection state."""

        self._ws.request_selection()

    def poll_graph_updates(self, *, timeout: float = 0.0) -> Optional[Dict[str, Any]]:
        """Retrieve next graph update emitted by backend."""

        try:
            return self._graph_updates.get(timeout=timeout)
        except Empty:
            return None

    # ------------------------------------------------------------------ #
    # Internal worker loop
    # ------------------------------------------------------------------ #
    def _run_loop(self) -> None:
        logging.basicConfig(level=os.getenv("FEDOC_MCP_BRIDGE_LOG", "INFO"))
        self._ws.start()
        while not self._stop_event.is_set():
            self._stop_event.wait(0.5)

    # ------------------------------------------------------------------ #
    # WebSocket event handlers
    # ------------------------------------------------------------------ #
    def _handle_hello(self, payload: Dict[str, Any]) -> None:
        data = payload.get("type"), payload
        LOGGER.debug("HELLO event received: %s", data)

    def _handle_graph_update(self, payload: Dict[str, Any]) -> None:
        LOGGER.debug("Graph update event: %s", payload)
        data = payload.get("data", {})
        if data:
            self._graph_updates.put(data)

    def _handle_selection(self, payload: Dict[str, Any]) -> None:
        data = payload.get("data", {})
        LOGGER.debug("Selection update received: %s", data)
        self._selection_snapshot = data or None

    def _handle_error(self, payload: Dict[str, Any]) -> None:
        LOGGER.error("Error event from hub: %s", json.dumps(payload))

