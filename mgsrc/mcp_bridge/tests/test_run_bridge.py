from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import mgsrc.mcp_bridge.mcp_bridge.run_bridge as core_run_bridge


class DummyBridge:
    def __init__(self):
        self.started = False
        self.stopped = False
        self.selection_requested = False
        self.snapshot = {"nodes": ["n1"], "edges": []}

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def request_selection_refresh(self):
        self.selection_requested = True

    def get_selection_snapshot(self):
        return self.snapshot


def test_main_once_prints_snapshot(monkeypatch, capsys):
    dummy = DummyBridge()
    monkeypatch.setattr(core_run_bridge, "MCPBridge", lambda config: dummy)

    exit_code = core_run_bridge.main(["--mode", "once", "--timeout", "0.0"])

    assert exit_code == 0
    assert dummy.started and dummy.stopped
    assert dummy.selection_requested
    captured = capsys.readouterr().out.strip()
    assert json.loads(captured) == dummy.snapshot


def test_main_daemon_calls_runner(monkeypatch):
    bridge = DummyBridge()
    monkeypatch.setattr(core_run_bridge, "MCPBridge", lambda config: bridge)

    called = {}

    def fake_daemon(fake_bridge):
        called["bridge"] = fake_bridge

    monkeypatch.setattr(core_run_bridge, "_run_daemon", fake_daemon)

    exit_code = core_run_bridge.main(["--mode", "daemon", "--log-level", "ERROR"])

    assert exit_code == 0
    assert called["bridge"] is bridge
