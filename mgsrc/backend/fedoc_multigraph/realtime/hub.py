"""WebSocket hub powered by Flask-SocketIO."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict, Optional

from flask import request
from flask_socketio import Namespace, SocketIO, emit, join_room, leave_room

PROTOCOL_VERSION = "1.0"
GRAPH_NAMESPACE = "/ws"
GRAPH_CHANNEL = "graph_updates"
SELECTION_CHANNEL = "selection_updates"
HEARTBEAT_INTERVAL_MS = 30_000
SELECTION_TTL_SECONDS = 30


class GraphHub:
    """Coordinate realtime messaging between backend, frontend and MCP clients."""

    def __init__(self) -> None:
        self.socketio = SocketIO(async_mode="threading", cors_allowed_origins="*")
        self.namespace = GRAPH_NAMESPACE
        self.default_channel = GRAPH_CHANNEL
        self.selection_channel = SELECTION_CHANNEL
        self.allowed_channels = {self.default_channel, self.selection_channel}
        self._clients: Dict[str, str] = {}
        self._selection_state: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def init_app(self, app) -> None:
        """Bind hub to Flask application and register namespace handlers."""

        self.reset()
        self.socketio.init_app(app, cors_allowed_origins="*")
        self.socketio.on_namespace(_GraphNamespace(self))
        app.extensions["graph_hub"] = self

    def reset(self) -> None:
        """Clear runtime state (used by tests)."""

        self._clients.clear()
        self._selection_state = None

    # ------------------------------------------------------------------ #
    # Client management helpers
    # ------------------------------------------------------------------ #
    def register_client(self, sid: str) -> str:
        client_id = str(uuid.uuid4())
        self._clients[sid] = client_id
        return client_id

    def unregister_client(self, sid: str) -> None:
        self._clients.pop(sid, None)

    def get_client_id(self, sid: str) -> Optional[str]:
        return self._clients.get(sid)

    # ------------------------------------------------------------------ #
    # Broadcast helpers
    # ------------------------------------------------------------------ #
    def broadcast_graph_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast graph update event to all listeners."""

        message = {
            "type": "graph_updated",
            "data": {
                **payload,
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        self.socketio.emit(
            "event",
            message,
            namespace=self.namespace,
            room=self.default_channel,
        )
        return message

    def broadcast_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast current selection to listeners and cache it."""

        data = payload.copy()
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if "expires_at" not in data:
            ttl = datetime.now(timezone.utc) + timedelta(seconds=SELECTION_TTL_SECONDS)
            data["expires_at"] = ttl.isoformat()

        self._selection_state = data

        message = {
            "type": "selected_nodes",
            "data": data,
        }
        self.socketio.emit(
            "event",
            message,
            namespace=self.namespace,
            room=self.selection_channel,
        )
        return message

    def current_selection(self) -> Dict[str, Any]:
        return self._selection_state or {
            "origin": "system",
            "nodes": [],
            "edges": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=SELECTION_TTL_SECONDS)).isoformat(),
        }


class _GraphNamespace(Namespace):
    """Socket.IO namespace implementing the JSON protocol defined for /ws."""

    def __init__(self, hub: GraphHub) -> None:
        super().__init__(hub.namespace)
        self._hub = hub

    # ------------------------------------------------------------------ #
    # Connection hooks
    # ------------------------------------------------------------------ #
    def on_connect(self):
        client_id = self._hub.register_client(request.sid)
        join_room(self._hub.default_channel)
        emit(
            "event",
            {
                "type": "hello",
                "protocol_version": PROTOCOL_VERSION,
                "client_id": client_id,
                "heartbeat_interval": HEARTBEAT_INTERVAL_MS,
            },
        )

    def on_disconnect(self):
        self._hub.unregister_client(request.sid)

    # ------------------------------------------------------------------ #
    # Client events
    # ------------------------------------------------------------------ #
    def on_client_event(self, data: Any):
        if not isinstance(data, dict):
            self._emit_error("invalid_payload", "Payload must be a JSON object.")
            return

        event_type = data.get("type")
        if not isinstance(event_type, str):
            self._emit_error("invalid_payload", "Field 'type' is required.")
            return

        handler = getattr(self, f"_handle_{event_type}", None)
        if handler is None:
            self._emit_error("unknown_event", f"Unsupported event type '{event_type}'.")
            return

        handler(data)

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _handle_subscribe(self, data: Dict[str, Any]) -> None:
        channel = data.get("channel")
        if channel not in self._hub.allowed_channels:
            self._emit_error("unknown_channel", f"Channel '{channel}' is not available.")
            return

        join_room(channel)
        emit(
            "event",
            {
                "type": "subscription_ack",
                "channel": channel,
                "status": "subscribed",
            },
        )

    def _handle_unsubscribe(self, data: Dict[str, Any]) -> None:
        channel = data.get("channel")
        if channel not in self._hub.allowed_channels:
            self._emit_error("unknown_channel", f"Channel '{channel}' is not available.")
            return

        leave_room(channel)
        emit(
            "event",
            {
                "type": "subscription_ack",
                "channel": channel,
                "status": "unsubscribed",
            },
        )

    def _handle_get_selected_nodes(self, _: Dict[str, Any]) -> None:
        emit(
            "event",
            {
                "type": "selected_nodes",
                "data": self._hub.current_selection(),
            },
        )

    def _handle_push_selection(self, data: Dict[str, Any]) -> None:
        payload = data.get("data", {})
        if not isinstance(payload, dict):
            self._emit_error("invalid_payload", "Field 'data' must be an object.")
            return

        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        origin = payload.get("origin", "unknown")

        if not isinstance(nodes, list) or not isinstance(edges, list):
            self._emit_error("invalid_payload", "Fields 'nodes' and 'edges' must be arrays.")
            return

        selection_payload = {
            "origin": origin,
            "nodes": nodes,
            "edges": edges,
            "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        }
        self._hub.broadcast_selection(selection_payload)

    def _handle_ping(self, _: Dict[str, Any]) -> None:
        emit(
            "event",
            {
                "type": "pong",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _emit_error(self, code: str, message: str) -> None:
        emit(
            "event",
            {
                "type": "error",
                "code": code,
                "message": message,
            },
        )


graph_hub = GraphHub()

