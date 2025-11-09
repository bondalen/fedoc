# Требования к каналу WebSocket `/ws` — 2025-11-09

**Статус:** черновик согласования  
**Заказчик:** backend + frontend команды multigraph  
**Связанные документы:**  
- [../../aa-main-docs/aa-project.md](../../aa-main-docs/aa-project.md#websocket-api) — сводное описание интерфейса  
- [../../aa-main-docs/bb-tasks.md](../../aa-main-docs/bb-tasks.md#13-websocket-и-инфраструктура) — блок задач 1.3.*  
- [../25-1109/testing-ci-deep-dive.md](testing-ci-deep-dive.md) — регламент тестирования (дополнить сценариями WebSocket после реализации)

---

## 1. Цель
Согласовать между backend и frontend команды протокол обмена данными через WebSocket `/ws` до начала реализации задач блока 1.3.x. Документ описывает:
- требования к подключению и аутентификации;
- структуру сообщений и событий;
- ожидания по устойчивости и мониторингу;
- точки интеграции с MCP Bridge.

## 2. Контекст
- REST API закрывает CRUD для блоков/дизайнов/проектов; realtime-событий нет.
- Frontend Graph Viewer ожидает push-уведомления об изменении графа и синхронизацию выделений.
- MCP Bridge (план 1.3.2) должен повторно использовать тот же канал, поэтому протокол должен быть нейтральным к типу клиента.

## 3. Требования к соединению
1. **Endpoint:** `ws://<host>:8080/ws` (production: через реверс-прокси `wss://`).
2. **Handshake:** стандартный WebSocket upgrade от HTTP(S); при успешном upgrade сервер отправляет событие `hello`.
3. **Аутентификация (MVP):** без токена; в сообщении `hello` сервер сообщает `client_id`. План расширения ― поддержка `Authorization: Bearer` (issue).
4. **Формат сообщений:** JSON в UTF-8, поле `type` обязательно.
5. **Версионирование:** поле `protocol_version` в событии `hello`. Клиенты при несовместимости закрывают соединение.

## 4. Модель каналов и подписок
- Каждый клиент автоматически подписан на `graph_updates`.
- Дополнительные каналы (позже): `selection_updates`, `system_notifications`.
- Сообщение подписки:
  ```json
  { "type": "subscribe", "channel": "graph_updates" }
  ```
- Сервер отвечает `subscription_ack`.

## 5. События Client → Server
- `subscribe` — запрос подписки (см. выше).
- `unsubscribe` — отказ от канала (сервер подтверждает `subscription_ack` с `"status": "unsubscribed"`).
- `get_selected_nodes` — запрос текущего выделения в Graph Viewer (сервер отвечает `selected_nodes`).
- `push_selection` — клиент сообщает о новом выделении (используется MCP Bridge).
  ```json
  {
    "type": "push_selection",
    "data": {
      "origin": "mcp" | "frontend",
      "nodes": ["graphid", "..."],
      "edges": ["graphid", "..."],
      "timestamp": "2025-11-09T14:57:00Z"
    }
  }
  ```
- `ping` — keepalive от клиента (сервер отвечает `pong`).

## 6. События Server → Client
- `hello` — сразу после handshake.
  ```json
  {
    "type": "hello",
    "protocol_version": "1.0",
    "client_id": "<uuid>",
    "heartbeat_interval": 30000
  }
  ```
- `subscription_ack` — подтверждение подписки/отписки.
- `graph_updated` — уведомление об изменении графа. Структура:
  ```json
  {
    "type": "graph_updated",
    "data": {
      "entity_type": "block" | "design" | "project",
      "entity_id": "<graphid|int>",
      "action": "created" | "updated" | "deleted",
      "source": "rest" | "seed" | "mcp",
      "snapshot": { /* опционально: payload сущности */ },
      "published_at": "2025-11-09T15:00:00Z"
    }
  }
  ```
- `selected_nodes` — ответ на `get_selected_nodes` и рассылка при `push_selection`. Поля:
  - `origin` — источник события.
  - `nodes`, `edges` — массивы идентификаторов.
  - `expires_at` — когда состояние считается устаревшим (мс).
- `pong` — ответ на `ping`.
- `error` — ошибки протокола (например, неизвестный тип, недоступный канал).

## 7. Устойчивость и мониторинг
- Сервер хранит последнюю активность клиента; если не было сообщений дольше `heartbeat_interval * 2`, соединение закрывается с кодом 4000.
- Логи:
  - INFO: handshake, подписки, закрытия.
  - DEBUG: входящие/исходящие payload (обрезанные до 2KB).
  - WARN: ошибки декодирования JSON, неизвестные типы.
- Метрики (Prometheus):
  - `ws_connections_active` — gauge.
  - `ws_messages_total{direction=…}` — counter.
  - `ws_disconnect_reason_total{code=…}` — counter.

## 8. Взаимодействие с MCP Bridge
- MCP Bridge выступает как клиент WebSocket; использует `push_selection` и слушает `selected_nodes`.
- Команда `mcp.select_nodes` внутри Cursor транслируется в `push_selection` с `origin="mcp"`.
- При изменении в backend (REST) backend эмитирует `graph_updated`; MCP Bridge решает, синхронизировать ли состояние в Cursor.

## 9. Требования к фронтенду
- Graph Viewer:
  - Отправляет `subscribe` и обрабатывает `graph_updated`.
  - Хранит `client_id` для корреляции (например, чтобы игнорировать собственные события при `push_selection`).
  - Поддерживает reconnect c экспоненциальной задержкой (1s, 2s, 5s, 10s).
  - При `error` с `code="unsupported_version"` предлагает перезагрузку.
- UI показывает индикатор статуса WebSocket (connected / reconnecting / failed).

## 10. План тестирования
1. **Unit:** сериализация/десериализация сообщений.
2. **Integration (pytest, метка `ws`):**
   - успешный handshake + `hello`;
   - подписка и получение `graph_updated` после изменения через REST;
   - `push_selection` → вещание `selected_nodes` всем клиентам.
3. **E2E (в дальнейшем):** Cypress-тест, проверяющий обновление графа без перезагрузки страницы.

## 11. Открытые вопросы
- Требуется ли авторизация на первом этапе? (по умолчанию `anonymous`).
- Каким образом REST операции инициируют события? (варианты: сигнал в сервисном слое или PostgreSQL LISTEN/NOTIFY).
- Какое поле использовать для идентификаторов в `graph_updated` (UUID vs graphid текст)?

---

**Следующие действия:**  
1. Утвердить формат событий с фронтендом (созвон 2025-11-10).  
2. Обновить `aa-project.md` раздел WebSocket с ссылкой на текущий документ.  
3. После реализации дополнить `testing-ci-deep-dive.md` сценариями WebSocket и настроить отдельный workflow.

