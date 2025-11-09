from __future__ import annotations

import uuid

import pytest

from fedoc_multigraph.realtime import PROTOCOL_VERSION, graph_hub


pytestmark = pytest.mark.integration


def _drain_events(client):
    events = []
    while True:
        batch = client.get_received(graph_hub.namespace)
        if not batch:
            break
        events.extend(batch)
    return events


def _extract_event(events, event_type):
    for event in events:
        if event.get("name") != "event":
            continue
        payload = event["args"][0]
        if payload.get("type") == event_type:
            return payload
    return None


def test_ws_handshake_returns_hello(app):
    graph_hub.reset()
    client = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    try:
        events = _drain_events(client)
        hello = _extract_event(events, "hello")
        assert hello is not None
        assert hello["protocol_version"] == PROTOCOL_VERSION
        assert "client_id" in hello and isinstance(hello["client_id"], str)
        assert hello["heartbeat_interval"] > 0
    finally:
        client.disconnect(namespace=graph_hub.namespace)


def test_ws_subscribe_and_acknowledge(app):
    graph_hub.reset()
    client = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    try:
        _drain_events(client)  # discard hello
        client.emit(
            "client_event",
            {"type": "subscribe", "channel": graph_hub.selection_channel},
            namespace=graph_hub.namespace,
        )
        events = _drain_events(client)
        ack = _extract_event(events, "subscription_ack")
        assert ack is not None
        assert ack["channel"] == graph_hub.selection_channel
        assert ack["status"] == "subscribed"
    finally:
        client.disconnect(namespace=graph_hub.namespace)


def test_ws_broadcast_graph_update_reaches_clients(app):
    graph_hub.reset()
    client_a = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    client_b = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    try:
        _drain_events(client_a)
        _drain_events(client_b)

        payload = {
            "entity_type": "block",
            "entity_id": str(uuid.uuid4()),
            "action": "created",
            "source": "tests",
        }
        graph_hub.broadcast_graph_update(payload)

        events_a = _drain_events(client_a)
        events_b = _drain_events(client_b)
        update_a = _extract_event(events_a, "graph_updated")
        update_b = _extract_event(events_b, "graph_updated")

        assert update_a is not None and update_b is not None
        assert update_a["data"]["entity_id"] == payload["entity_id"]
        assert update_b["data"]["action"] == payload["action"]
        assert "published_at" in update_a["data"]
    finally:
        client_a.disconnect(namespace=graph_hub.namespace)
        client_b.disconnect(namespace=graph_hub.namespace)


def test_ws_push_selection_broadcasts_and_can_be_retrieved(app):
    graph_hub.reset()
    publisher = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    listener = graph_hub.socketio.test_client(app, namespace=graph_hub.namespace)
    try:
        _drain_events(publisher)
        _drain_events(listener)

        for client in (publisher, listener):
            client.emit(
                "client_event",
                {"type": "subscribe", "channel": graph_hub.selection_channel},
                namespace=graph_hub.namespace,
            )
            _drain_events(client)  # subscription ack

        selection_payload = {
            "origin": "test-suite",
            "nodes": ["node-1", "node-2"],
            "edges": ["edge-1"],
        }
        publisher.emit(
            "client_event",
            {"type": "push_selection", "data": selection_payload},
            namespace=graph_hub.namespace,
        )

        listener_events = _drain_events(listener)
        broadcast = _extract_event(listener_events, "selected_nodes")
        assert broadcast is not None
        assert broadcast["data"]["nodes"] == selection_payload["nodes"]
        assert broadcast["data"]["origin"] == "test-suite"

        listener.emit(
            "client_event",
            {"type": "get_selected_nodes"},
            namespace=graph_hub.namespace,
        )
        snapshot = _extract_event(_drain_events(listener), "selected_nodes")
        assert snapshot is not None
        assert snapshot["data"]["nodes"] == selection_payload["nodes"]
        assert snapshot["data"]["edges"] == selection_payload["edges"]
    finally:
        publisher.disconnect(namespace=graph_hub.namespace)
        listener.disconnect(namespace=graph_hub.namespace)

