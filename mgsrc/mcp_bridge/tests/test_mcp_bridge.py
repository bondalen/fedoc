from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_bridge import BridgeConfig, MCPBridge


class DummyBridge(MagicMock):
    def __init__(self):
        super().__init__()
        self.listeners = {}

    def add_listener(self, event_type, callback):
        self.listeners[event_type] = callback

    def broadcast_selection(self, nodes, edges, **kwargs):
        self.called_with = (list(nodes), list(edges), kwargs)

    def request_selection(self):
        self.requested = True

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_push_selection_uses_underlying_bridge(monkeypatch):
    config = BridgeConfig()
    dummy_ws = DummyBridge()
    monkeypatch.setattr("mgsrc.mcp_bridge.mcp_bridge.server.WebSocketBridge", lambda cfg: dummy_ws)

    bridge = MCPBridge(config)
    bridge.push_selection(["a"], ["b"])

    assert dummy_ws.called_with == (["a"], ["b"], {})


def test_selection_snapshot_updates(monkeypatch):
    config = BridgeConfig()
    dummy_ws = DummyBridge()
    monkeypatch.setattr("mgsrc.mcp_bridge.mcp_bridge.server.WebSocketBridge", lambda cfg: dummy_ws)

    bridge = MCPBridge(config)
    callback = dummy_ws.listeners["selected_nodes"]
    callback({"data": {"nodes": ["x"], "edges": []}})

    assert bridge.get_selection_snapshot() == {"nodes": ["x"], "edges": []}

