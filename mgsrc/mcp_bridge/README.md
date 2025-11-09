# fedoc multigraph — MCP Bridge

**Статус:** 🚧 в разработке  
**Назначение:** связка между backend WebSocket hub (`/ws`) и будущим MCP-сервером multigraph.  

## Возможности
- Поддерживает постоянно активное соединение с `/ws` через `python-socketio`.
- Автоматически подписывается на каналы `graph_updates` и `selection_updates`.
- Предоставляет API для:
  - отправки выделений из MCP (`push_selection`);
  - получения последнего состояния выделения (`get_selection_snapshot`);
  - получения очереди событий графа (`poll_graph_updates`).

## Структура
```
mgsrc/mcp_bridge/
├── mcp_bridge/
│   ├── __init__.py            # Экспорт BridgeConfig, MCPBridge, WebSocketBridge
│   ├── config.py              # Конфигурация из переменных окружения
│   ├── server.py              # Внешний API для MCP
│   └── websocket_bridge.py    # Обёртка над python-socketio.Client
├── tests/
│   └── test_websocket_bridge.py
└── requirements.txt
```

## Установка для разработки
```bash
cd mgsrc/mcp_bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Запуск Bridge (пример)
```python
from mcp_bridge import MCPBridge

bridge = MCPBridge()
bridge.start()

# Запросить снимок выделения
bridge.request_selection_refresh()
snapshot = bridge.get_selection_snapshot()

# Отправить собственное выделение
bridge.push_selection(["vertex-1"], ["edge-9"])
```

## Переменные окружения
| Переменная | Назначение | Значение по умолчанию |
| ---------- | ----------- | --------------------- |
| `FEDOC_WS_URL` | URL WebSocket хаба | `ws://localhost:8080/ws` |
| `FEDOC_WS_RECONNECT_DELAY` | Пауза перед повторным подключением (сек) | `5.0` |
| `FEDOC_WS_SELECTION_CHANNEL` | Канал для выделений | `selection_updates` |
| `FEDOC_WS_GRAPH_CHANNEL` | Канал для событий графа | `graph_updates` |
| `FEDOC_MCP_ORIGIN` | Значение `origin` при отправке выделений | `mcp` |

## Тесты
```bash
cd /home/alex/fedoc
pytest mgsrc/mcp_bridge/tests
```

