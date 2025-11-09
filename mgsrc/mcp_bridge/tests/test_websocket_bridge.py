from __future__ import annotations

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from mcp_bridge import BridgeConfig, WebSocketBridge


class DummyClient:
    """Minimal stub of socketio.Client for unit tests."""

    def __init__(self):
        self._callbacks = {}
        self.emitted = []

    def on(self, event, handler=None, namespace=None):
        self._callbacks[(event, namespace)] = handler

    def emit(self, event, payload, namespace=None):
        self.emitted.append((event, payload, namespace))

    def connect(self, *args, **kwargs):
        handler = self._callbacks.get(("connect", "/ws"))
        if handler:
            handler()

    def disconnect(self):
        handler = self._callbacks.get(("disconnect", "/ws"))
        if handler:
            handler()

    def trigger(self, event, payload):
        handler = self._callbacks.get((event, "/ws"))
        assert handler is not None, f"handler for {(event, '/ws')} not registered"
        handler(payload)


@pytest.fixture
def bridge_with_dummy_client():
    client = DummyClient()
    config = BridgeConfig(websocket_url="ws://test/ws")
    bridge = WebSocketBridge(config, client=client)
    return bridge, client


def test_subscribes_to_default_channels_on_connect(bridge_with_dummy_client):
    bridge, client = bridge_with_dummy_client

    bridge._subscribe_default_channels()

    payloads = [payload for (_, payload, _) in client.emitted]
    assert {"type": "subscribe", "channel": "graph_updates"} in payloads
    assert {"type": "subscribe", "channel": "selection_updates"} in payloads


def test_dispatches_events_to_registered_callbacks(bridge_with_dummy_client):
    bridge, client = bridge_with_dummy_client
    events = []

    def callback(payload):
        events.append(payload)

    bridge.add_listener("graph_updated", callback)
    client.trigger("event", {"type": "graph_updated", "data": {"entity_id": "x"}})

    assert len(events) == 1
    assert events[0]["data"]["entity_id"] == "x"


def test_broadcast_selection_uses_client_event(bridge_with_dummy_client):
    bridge, client = bridge_with_dummy_client

    bridge.broadcast_selection(["n1"], ["e1"], origin="test")
    assert client.emitted[-1] == (
        "client_event",
        {"type": "push_selection", "data": {"origin": "test", "nodes": ["n1"], "edges": ["e1"]}},
        "/ws",
    )

