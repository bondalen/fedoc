# Интеграция Graph Viewer в MCP-сервер

**Дата:** 2025-10-15  
**Версия:** 0.2.0  
**Статус:** ✅ Этап 1 завершен

---

## 📋 Выполненная работа

### 1. Реорганизация структуры Graph Viewer

**Создана папка `backend/`:**
```
src/lib/graph_viewer/
├── backend/                      # ➕ Новая структура
│   ├── __init__.py              
│   ├── api_server.py            # ⬅️ Перемещен из корня
│   ├── tunnel_manager.py        # ➕ Управление SSH туннелями
│   └── process_manager.py       # ➕ Управление процессами
├── frontend/                     # Vue.js интерфейс
├── frontend-alpine/              # Бэкап Alpine.js
└── README.md
```

**Удалены устаревшие файлы:**
- ❌ `viewer.py` (PyVis версия)
- ❌ `web_viewer.py` (промежуточная версия)

---

### 2. Созданные модули

#### `tunnel_manager.py`
Управление SSH туннелями к удаленному ArangoDB.

**Функции:**
- `check_tunnel()` - проверка существующего туннеля
- `create_tunnel()` - создание нового туннеля
- `close_tunnel()` - закрытие туннеля
- `ensure_tunnel()` - обеспечение активного туннеля
- `get_status()` - статус туннеля

#### `process_manager.py`
Управление процессами API и Vite серверов.

**Функции:**
- `start_api_server()` - запуск API сервера
- `start_vite_server()` - запуск Vite dev сервера
- `stop_api_server()` - остановка API сервера
- `stop_vite_server()` - остановка Vite сервера
- `start_all()` - запуск всех компонентов
- `stop_all()` - остановка всех компонентов
- `get_status()` - статус процессов

---

### 3. MCP обработчик

**Файл:** `src/mcp_server/handlers/graph_viewer_manager.py`

**Реализованные команды:**

#### `open_graph_viewer(project, auto_open_browser)`
Запуск системы визуализации графа.

**Что делает:**
1. ✅ Проверяет/создает SSH туннель
2. ✅ Запускает API сервер
3. ✅ Запускает Vite dev сервер
4. ✅ Открывает браузер (опционально)

**Примеры использования:**
```python
open_graph_viewer()                          # Все проекты
open_graph_viewer(project='fepro')          # Конкретный проект
open_graph_viewer(auto_open_browser=False)  # Без браузера
```

#### `graph_viewer_status()`
Проверка статуса компонентов.

**Возвращает:**
- Статус SSH туннеля
- Статус ArangoDB
- Статус API сервера
- Статус Vite сервера
- Общий статус системы
- URL интерфейса

#### `stop_graph_viewer(stop_tunnel, force)`
Остановка компонентов.

**Параметры:**
- `stop_tunnel` - также закрыть SSH туннель
- `force` - принудительная остановка (kill -9)

---

### 4. Интеграция в MCP-сервер

**Обновлен:** `src/mcp_server/server.py`

**Изменения:**
- ✅ Версия сервера: 0.1.0 → 0.2.0
- ✅ Импорт обработчиков Graph Viewer
- ✅ Регистрация 3 инструментов
- ✅ Отображение списка команд
- ✅ Примеры использования

**Обновлен:** `src/mcp_server/config.py`

**Добавлено:**
```python
GRAPH_VIEWER_SSH_HOST = "vuege-server"
GRAPH_VIEWER_API_PORT = 8899
GRAPH_VIEWER_FRONTEND_PORT = 5173
```

---

## ✅ Результаты тестирования

### Тест 1: Импорты
```bash
✅ Импорты работают корректно
```

### Тест 2: Базовые функции
```bash
✅ SSH туннель создается/проверяется
✅ API сервер запускается/останавливается
✅ Vite сервер запускается/останавливается
✅ Статус отображается корректно
```

### Тест 3: MCP интеграция
```bash
✅ MCP сервер запускается
✅ 3 инструмента зарегистрированы
✅ Функции вызываются через MCP API
✅ Параметры передаются корректно
```

---

## 🎯 Доступные команды

### 1. **open_graph_viewer**
Открыть систему визуализации графа

**Использование в Cursor AI:**
- "Открой управление графом"
- "Запусти graph viewer для проекта FEPRO"
- "Покажи визуализацию"

### 2. **graph_viewer_status**
Проверить статус системы

**Использование в Cursor AI:**
- "Проверь статус graph viewer"
- "Работает ли визуализация?"

### 3. **stop_graph_viewer**
Остановить систему

**Использование в Cursor AI:**
- "Останови graph viewer"
- "Выключи визуализацию"

---

## 📊 Статистика

**Создано файлов:** 4
- `backend/__init__.py` (8 строк)
- `backend/tunnel_manager.py` (168 строк)
- `backend/process_manager.py` (318 строк)
- `handlers/graph_viewer_manager.py` (277 строк)

**Обновлено файлов:** 4
- `graph_viewer/__init__.py`
- `mcp_server/server.py`
- `mcp_server/config.py`
- `mcp_server/README.md`

**Удалено файлов:** 2
- `viewer.py`
- `web_viewer.py`

**Всего строк кода:** ~771 строка

---

## 🚀 Следующие шаги (Этап 2)

### Запланированные команды:

1. **query_graph** - выполнение AQL запросов
2. **get_node_info** - информация о узле + контекст
3. **export_graph** - экспорт в разные форматы
4. **analyze_project_graph** - анализ структуры

---

## 🔗 Связанные документы

- [Решение 002: MCP Integration](002-mcp-integration.md)
- [Решение 003: Graph Viewer Architecture](003-graph-viewer-arch.md)
- [Vue Migration Complete](MIGRATION_COMPLETE.md)
- [MCP Server README](../../src/mcp_server/README.md)
- [Graph Viewer README](../../src/lib/graph_viewer/README.md)

---

**Автор:** Александр + Claude (Cursor AI)  
**Дата:** 2025-10-15











