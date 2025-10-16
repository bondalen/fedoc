# Интеграция Graph Viewer с Cursor AI через WebSocket

**Дата:** 16 октября 2025  
**Участники:** Александр, AI Assistant  
**Окружение:** WSL2 (Ubuntu), Fedora 42

## 📋 Краткое описание

Реализована полноценная интеграция между Graph Viewer (браузерный интерфейс) и Cursor AI через WebSocket для интерактивной работы с объектами графа.

## 🎯 Основная задача

Создать возможность выбирать объекты в Graph Viewer в браузере и получать детальную информацию о них в Cursor AI для дальнейшей работы.

## 🔧 Реализованная функциональность

### Пользовательский сценарий:
1. Пользователь выбирает объекты в графе (Ctrl+Click)
2. Выбранные объекты отображаются в строке выборки внизу браузера
3. Пользователь пишет в Cursor AI: "Покажи выбранные объекты из Graph Viewer"
4. AI получает через WebSocket детальную информацию об объектах
5. Пользователь может дать инструкции что делать с этими объектами

### Технические особенности:
- **Двусторонняя связь:** WebSocket для pull-запросов от бэкенда к фронтенду
- **Визуальная обратная связь:** Строка выборки с цветными плашками
- **Детальная информация:** ID, название, тип, описание узлов; связи между рёбрами
- **Синхронизация:** Строгое соответствие выборки в графе и в строке выборки

## 📦 Архитектура решения

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  Graph Viewer   │ ←─────────────────→ │   API Server     │
│   (Browser)     │   socket.io-client  │   (Flask)        │
│   Vue.js 3      │                     │   Flask-SocketIO │
└─────────────────┘                     └──────────────────┘
                                                 ↑
                                                 │ HTTP
                                                 │
                                        ┌────────┴────────┐
                                        │   MCP Server    │
                                        │   (Cursor AI)   │
                                        └─────────────────┘
```

### Поток данных:
1. **Cursor AI** вызывает MCP команду `get_selected_nodes()`
2. **MCP Server** делает HTTP GET к `/api/request_selection`
3. **API Server** отправляет WebSocket событие `request_selection`
4. **Browser** получает событие и отправляет `selection_response` с данными
5. **API Server** возвращает данные в MCP Server
6. **Cursor AI** показывает результат пользователю

## 🛠️ Технический стек

### Backend:
- **Python 3.11** - основной язык
- **Flask 3.0+** - веб-фреймворк
- **Flask-SocketIO 5.3+** - WebSocket поддержка
- **Flask-CORS 4.0+** - CORS политика

### Frontend:
- **Vue.js 3** - UI фреймворк
- **Pinia** - state management
- **socket.io-client 4.8+** - WebSocket клиент
- **vis-network** - визуализация графа
- **Vite** - dev сервер и сборка

### Инфраструктура:
- **ArangoDB 3.11** - графовая БД
- **SSH Tunnel** - безопасное подключение к БД
- **WSL2** - окружение разработки

## 📝 Изменённые файлы

### Backend:

#### `requirements.txt`
```python
flask>=3.0.0
flask-socketio>=5.3.0
flask-cors>=4.0.0
python-socketio>=5.11.0
pyyaml
requests
```

#### `src/lib/graph_viewer/backend/api_server.py`
- Переход с HTTPServer на Flask + Flask-SocketIO
- WebSocket обработчики: `connect`, `disconnect`, `selection_response`
- Новая функция `request_selection_from_browser()` для pull-запросов
- Endpoint `/api/request_selection` для MCP команды
- Сохранение всех существующих REST endpoints

#### `src/mcp_server/handlers/graph_viewer_manager.py`
- Новая функция `get_selected_nodes()` - MCP команда
- HTTP запрос к API серверу для получения выборки
- Форматирование данных для отображения в чате
- Обработка timeout и ошибок

#### `src/mcp_server/server.py`
- Регистрация инструмента `get_selected_nodes`
- Обработчик `_handle_get_selected_nodes`
- Интеграция с graph_viewer_manager

### Frontend:

#### `src/lib/graph_viewer/frontend/package.json`
```json
"dependencies": {
  "socket.io-client": "^4.8.1",
  "pinia": "^3.0.3",
  "vis-data": "^8.0.3",
  "vis-network": "^10.0.2",
  "vue": "^3.5.22"
}
```

#### `src/lib/graph_viewer/frontend/src/stores/graph.js`
- Новое состояние: `selectedNodesList`, `selectedEdgesList`
- WebSocket состояние: `socket`, `isSocketConnected`
- Методы:
  - `initWebSocket()` - инициализация соединения
  - `closeWebSocket()` - закрытие соединения
  - `sendSelectionToServer()` - отправка выборки по WebSocket
  - `updateSelectedNodes()` - обновление списка узлов
  - `updateSelectedEdges()` - обновление списка рёбер
  - `clearSelection()` - очистка выборки

#### `src/lib/graph_viewer/frontend/src/components/SelectionBar.vue` (NEW)
- Новый компонент для отображения выбранных объектов
- Цветные плашки (chips) с именами объектов:
  - Синие - концепты (concept)
  - Зелёные - технологии (technology)
  - Оранжевые - рёбра (edge)
- Иконка 🔗 для рёбер с именами связанных узлов
- Клик по плашке фокусирует объект в графе
- Горизонтальная прокрутка для множества объектов
- Фиксированная высота 50-60px

#### `src/lib/graph_viewer/frontend/src/components/GraphCanvas.vue`
- Включён multiselect: `interaction.multiselect: true`
- Обработчик `select` для синхронизации выборки со store
- Вызов `store.updateSelectedNodes()` и `store.updateSelectedEdges()`
- Обработчики `deselectNode` и `deselectEdge` для очистки

#### `src/lib/graph_viewer/frontend/src/components/GraphViewer.vue`
- Добавлен компонент `<SelectionBar />`
- `onMounted` - инициализация WebSocket
- `onUnmounted` - закрытие WebSocket

#### `src/lib/graph_viewer/frontend/vite.config.js`
- Исправлен прокси для `/api` запросов
- `rewrite: (path) => path.replace(/^\/api/, '/api')`

### Конфигурация:

#### `config/machines/alex-User-PC.yaml` (NEW)
```yaml
hostname: "User-PC"
username: "alex"
os: "linux"
distribution: "WSL2"
kernel: "5.15.167.4-microsoft-standard-WSL2"

project:
  root: "/home/alex/fedoc"
  venv: "/home/alex/fedoc/venv"
  venv_python: "/home/alex/fedoc/venv/bin/python"
  venv_pip: "/home/alex/fedoc/venv/bin/pip"

ssh:
  enabled: true
  local_port: 8529
  remote_host: "176.124.215.24"
  remote_port: 8529
  user: "root"

arango:
  host: "127.0.0.1"
  port: 8529
  database: "fedoc"
  username: "root"

api:
  host: "127.0.0.1"
  port: 8899

vite:
  host: "127.0.0.1"
  port: 5173

options:
  auto_open_browser: false
  use_windows_browser: true
  wsl: true
```

#### `config/.secrets.env`
```bash
ARANGO_PASSWORD=fedoc_dev_2025
```

## 🐛 Решённые проблемы

### 1. Externally-managed-environment
**Проблема:** Невозможность установки pip пакетов в WSL Ubuntu  
**Решение:** Создание и использование Python virtual environment

### 2. 404 на /api/nodes
**Проблема:** Vite dev server не проксировал запросы к API  
**Решение:** Исправление `rewrite` в vite.config.js

### 3. Отсутствие модуля yaml
**Проблема:** `ModuleNotFoundError: No module named 'yaml'`  
**Решение:** Установка `pyyaml` в venv

### 4. WSL специфика
**Проблема:** Отличия путей, хостнейма, отсутствие GUI  
**Решение:** Создание машинного профиля с WSL настройками

## ✅ Результаты тестирования

### Запуск системы:
```bash
✓ SSH туннель активен (PID: 4574) на порту 8529
✓ API сервер запущен (PID: 4578) на порту 8899  
✓ Vite сервер запущен (PID: 4976) на порту 5173
✓ WebSocket соединение установлено
```

### Тестовый запрос:
**Команда:** "Покажи выбранные объекты из Graph Viewer"

**Результат:**
```
✅ Выбрано в Graph Viewer:

📦 Узлы (2):
1. canonical_nodes/c:layer
   Название: Слой
   Тип: concept
   Описание: Архитектурный слой приложения (frontend, backend)

2. canonical_nodes/t:arangodb@3.11
   Название: ArangoDB
   Тип: technology
   Описание: Multi-Model СУБД (Document + Graph + Key-Value)

🔗 Рёбра (1):
1. project_relations/85275
   От: canonical_nodes/c:dev-objects
   К: canonical_nodes/c:layer
   Проекты: fepro, femsq
   Тип связи: contains
```

## 📊 Статистика коммита

```
Commit: 78403e8
Files changed: 12
Insertions: 1,125 lines
Deletions: 195 lines
New files: 2
```

### Созданные файлы:
- `config/machines/alex-User-PC.yaml`
- `src/lib/graph_viewer/frontend/src/components/SelectionBar.vue`

### Изменённые файлы:
- `requirements.txt`
- `src/lib/graph_viewer/backend/api_server.py`
- `src/lib/graph_viewer/frontend/package.json`
- `src/lib/graph_viewer/frontend/package-lock.json`
- `src/lib/graph_viewer/frontend/src/components/GraphCanvas.vue`
- `src/lib/graph_viewer/frontend/src/components/GraphViewer.vue`
- `src/lib/graph_viewer/frontend/src/stores/graph.js`
- `src/lib/graph_viewer/frontend/vite.config.js`
- `src/mcp_server/handlers/graph_viewer_manager.py`
- `src/mcp_server/server.py`

## 🚀 Возможности для развития

### Краткосрочные:
1. Сохранение истории выборок
2. Именованные выборки (наборы)
3. Экспорт выборки в JSON/YAML
4. Фильтрация объектов в строке выборки

### Среднесрочные:
1. Batch операции над выбранными объектами
2. Создание связей между выбранными узлами
3. Групповое редактирование свойств
4. Визуализация подграфа из выборки

### Долгосрочные:
1. AI-анализ выборки (поиск паттернов)
2. Рекомендации по архитектуре на основе выборки
3. Автоматическая генерация документации
4. Интеграция с системами контроля версий

## 📚 Связанные документы

- `docs-preliminary/chats/chat-2025-10-16-config-system-and-machine-profiles.md` - Система конфигурации
- `docs-preliminary/project-history/chat-2025-10-16_cursor_interactive.md` - Первоначальный план интеграции

## 🎓 Извлечённые уроки

1. **WebSocket для pull-запросов** - эффективное решение для двусторонней связи
2. **WSL требует специфичной конфигурации** - пути, браузер, hostname
3. **Virtual environments критичны** - особенно в современных Linux дистрибутивах
4. **Vite proxy требует внимания** - легко ошибиться в rewrite правилах
5. **Визуальная обратная связь важна** - строка выборки значительно улучшает UX

## 🏁 Заключение

Интеграция Graph Viewer с Cursor AI через WebSocket успешно реализована и протестирована. Система работает стабильно, предоставляет интуитивный интерфейс для работы с объектами графа и открывает новые возможности для интерактивной разработки с помощью AI.

**Статус:** ✅ Завершено и синхронизировано с GitHub  
**Следующий шаг:** Использование в реальных сценариях разработки

