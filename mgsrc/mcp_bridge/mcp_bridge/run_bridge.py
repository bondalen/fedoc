# SPDX-License-Identifier: MIT
"""Command-line entry point for running the MCP Bridge."""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from threading import Event
from typing import Optional

from .config import BridgeConfig
from .server import MCPBridge

SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)


def _configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="fedoc multigraph MCP Bridge runner")
    parser.add_argument(
        "--mode",
        choices=["daemon", "once"],
        default="daemon",
        help="Режим работы: daemon — непрерывный запуск, once — одиночный запрос selection",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Таймаут ожидания обновления selection (mode=once), секунды",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Уровень логирования (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args(argv)


def _run_daemon(bridge: MCPBridge) -> None:
    stop_event = Event()

    def _handler(signum, frame):  # noqa: D401, W0613
        logging.getLogger(__name__).info("Получен сигнал %s, останавливаем Bridge", signum)
        stop_event.set()

    for sig in SHUTDOWN_SIGNALS:
        signal.signal(sig, _handler)

    bridge.start()
    try:
        while not stop_event.is_set():
            time.sleep(1.0)
    finally:
        bridge.stop()


def _run_once(bridge: MCPBridge, timeout: float) -> None:
    bridge.start()
    try:
        bridge.request_selection_refresh()
        time.sleep(max(timeout, 0.1))
        snapshot = bridge.get_selection_snapshot()
        print(json.dumps(snapshot or {}), flush=True)
    finally:
        bridge.stop()


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.log_level)

    config = BridgeConfig.from_env()
    bridge = MCPBridge(config)

    if args.mode == "daemon":
        _run_daemon(bridge)
    else:
        _run_once(bridge, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
