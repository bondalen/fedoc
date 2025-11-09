"""Client wrapper around the backend WebSocket hub."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Iterable, Optional

import socketio

from .config import BridgeConfig

LOGGER = logging.getLogger(__name__)

EventCallback = Callable[[Dict[str, Any]], None]


class WebSocketBridge:
    """High-level wrapper over the multigraph WebSocket hub."""

    def __init__(
        self,
        config: BridgeConfig,
        *,
        client: Optional[socketio.Client] = None,
    ) -> None:
        self._config = config
        self._client = client or socketio.Client(reconnection=False, logger=False)
        self._client.on("connect", self._on_connect, namespace="/ws")
        self._client.on("disconnect", self._on_disconnect, namespace="/ws")
        self._client.on("event", self._on_event, namespace="/ws")

        self._connected = threading.Event()
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()

        self._listeners: Dict[str, set[EventCallback]] = {
            "hello": set(),
            "graph_updated": set(),
            "selected_nodes": set(),
            "error": set(),
            "subscription_ack": set(),
        }

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Establish the WebSocket connection with retry loop."""

        if self._connected.is_set():
            LOGGER.debug("WebSocketBridge already connected.")
            return

        self._stop_flag.clear()
        while not self._stop_flag.is_set():
            try:
                LOGGER.info("Connecting to WebSocket hub at %s", self._config.websocket_url)
                self._client.connect(
                    self._config.websocket_url,
                    namespaces=["/ws"],
                    wait=True,
                )
                if self._connected.wait(timeout=5):
                    LOGGER.info("WebSocketBridge connected.")
                    self._subscribe_default_channels()
                    return
            except Exception as exc:  # pragma: no cover - actual network failure
                LOGGER.warning("WebSocket connection failed: %s", exc)
                time.sleep(self._config.reconnect_delay)

    def stop(self) -> None:
        """Terminate the connection."""

        self._stop_flag.set()
        if self._connected.is_set():
            LOGGER.info("Disconnecting WebSocketBridge.")
            self._client.disconnect()
        self._connected.clear()

    # ------------------------------------------------------------------ #
    # Event subscription
    # ------------------------------------------------------------------ #
    def add_listener(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for a particular event type."""

        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = set()
            self._listeners[event_type].add(callback)

    def remove_listener(self, event_type: str, callback: EventCallback) -> None:
        """Remove a previously registered callback."""

        with self._lock:
            listeners = self._listeners.get(event_type)
            if listeners and callback in listeners:
                listeners.remove(callback)

    def _emit_to_listeners(self, event_type: str, payload: Dict[str, Any]) -> None:
        callbacks = list(self._listeners.get(event_type, ()))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception:  # pragma: no cover - defensive logging
                LOGGER.exception("Unhandled exception in WebSocket listener '%s'", event_type)

    # ------------------------------------------------------------------ #
    # Client API
    # ------------------------------------------------------------------ #
    def broadcast_selection(self, nodes: Iterable[str], edges: Iterable[str], *, origin: Optional[str] = None) -> None:
        """Send selection update to the hub."""

        message = {
            "type": "push_selection",
            "data": {
                "origin": origin or self._config.client_origin,
                "nodes": list(nodes),
                "edges": list(edges),
            },
        }
        LOGGER.debug("Emitting push_selection %s", message)
        self._client.emit("client_event", message, namespace="/ws")

    def request_selection(self) -> None:
        """Request current selection snapshot."""

        LOGGER.debug("Requesting selected_nodes snapshot.")
        message = {"type": "get_selected_nodes"}
        self._client.emit("client_event", message, namespace="/ws")

    # ------------------------------------------------------------------ #
    # Socket event handlers
    # ------------------------------------------------------------------ #
    def _on_connect(self) -> None:
        LOGGER.debug("SocketIO client connected.")
        self._connected.set()

    def _on_disconnect(self) -> None:
        LOGGER.debug("SocketIO client disconnected.")
        self._connected.clear()

        if not self._stop_flag.is_set():
            LOGGER.info("Connection lost, retrying in %.1f seconds.", self._config.reconnect_delay)
            time.sleep(self._config.reconnect_delay)
            if not self._stop_flag.is_set():
                self.start()

    def _on_event(self, data: Dict[str, Any]) -> None:
        event_type = (data or {}).get("type")
        if not event_type:
            LOGGER.debug("Received event without type: %s", data)
            return
        LOGGER.debug("Received event: %s", data)
        self._emit_to_listeners(event_type, data)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _subscribe_default_channels(self) -> None:
        for channel in {self._config.graph_channel, self._config.selection_channel}:
            message = {"type": "subscribe", "channel": channel}
            LOGGER.debug("Subscribing to channel %s", channel)
            self._client.emit("client_event", message, namespace="/ws")

