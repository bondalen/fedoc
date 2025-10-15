# fedoc MCP Server

MCP-сервер для интеграции проекта fedoc с Cursor AI.

## 🎯 Назначение

Предоставляет доступ к функциональности fedoc через Model Context Protocol (MCP):
- ✅ **Визуализация графов проектов** - интерактивный Graph Viewer
- 🚧 Запросы к документации
- 🚧 Управление правилами
- 🚧 Работа с проектами

## 🚀 Установка

```bash
cd src/mcp_server
pip install -r requirements.txt
```

## ⚙️ Конфигурация

Добавьте в `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "fedoc": {
      "command": "python",
      "args": ["/home/alex/projects/rules/fedoc/src/mcp_server/server.py"],
      "env": {
        "ARANGO_HOST": "http://localhost:8529",
        "ARANGO_DB": "fedoc",
        "ARANGO_USER": "root",
        "ARANGO_PASSWORD": "aR@ng0Pr0d2025xK9mN8pL"
      },
      "description": "fedoc MCP - управление проектной документацией"
    }
  }
}
```

## 📋 Команды

### ✅ open_graph_viewer
**Открыть систему визуализации графа в браузере**

Автоматически:
1. Проверяет/создает SSH туннель к ArangoDB
2. Запускает API сервер (если не запущен)
3. Запускает Vite dev сервер (если не запущен)
4. Открывает браузер с интерфейсом

**Параметры:**
- `project` (str, optional): Фильтр по проекту (fepro, femsq, fedoc) или None для всех
- `auto_open_browser` (bool): Автоматически открыть браузер (default: True)

**Примеры использования в Cursor AI:**
```
Открой управление графом
Запусти graph viewer для проекта FEPRO
Покажи визуализацию
```

**Python API:**
```python
from mcp_server.handlers.graph_viewer_manager import open_graph_viewer

# Открыть для всех проектов
open_graph_viewer()

# Открыть для конкретного проекта
open_graph_viewer(project='fepro')

# Запустить без открытия браузера
open_graph_viewer(auto_open_browser=False)
```

---

### ✅ graph_viewer_status
**Проверить статус компонентов Graph Viewer**

Показывает статус:
- SSH туннеля
- ArangoDB доступности
- API сервера
- Vite dev сервера

**Примеры использования в Cursor AI:**
```
Проверь статус graph viewer
Работает ли визуализация?
```

**Python API:**
```python
from mcp_server.handlers.graph_viewer_manager import graph_viewer_status

status = graph_viewer_status()
print(status)
```

---

### ✅ stop_graph_viewer
**Остановить систему визуализации графа**

**Параметры:**
- `stop_tunnel` (bool): Также закрыть SSH туннель (default: False)
- `force` (bool): Принудительное завершение процессов (default: False)

**Примеры использования в Cursor AI:**
```
Останови graph viewer
Выключи визуализацию
Закрой graph viewer и туннель
```

**Python API:**
```python
from mcp_server.handlers.graph_viewer_manager import stop_graph_viewer

# Остановить только процессы (туннель оставить)
stop_graph_viewer()

# Остановить все включая туннель
stop_graph_viewer(stop_tunnel=True)

# Принудительная остановка
stop_graph_viewer(force=True)
```

---

### 🚧 query_graph (планируется)
Выполнить AQL запрос к графу

### 🚧 get_node_info (планируется)
Получить информацию о узле графа

### 🚧 export_graph (планируется)
Экспортировать граф в различных форматах

### 🚧 get_project_docs (планируется)
Получить документацию проекта

### 🚧 list_projects (планируется)
Список всех проектов

### 🚧 get_rules (планируется)
Получить правила для артефакта

## 🔧 Разработка

**Статус:** ✅ Этап 1 завершен

**Текущая функциональность:**
- ✅ Базовая структура сервера
- ✅ Интеграция с Graph Viewer
- ✅ Автоматическое управление SSH туннелями
- ✅ Управление процессами (API + Vite)
- ✅ 3 рабочих команды (open, status, stop)
- ⏳ Полный MCP протокол (в разработке)
- ⏳ Расширенные команды (query, export, analysis)

**Архитектура:**
```
src/
├── lib/
│   └── graph_viewer/
│       ├── backend/              # Python компоненты
│       │   ├── api_server.py    # REST API
│       │   ├── tunnel_manager.py # SSH туннели
│       │   └── process_manager.py # Управление процессами
│       └── frontend/             # Vue.js интерфейс
│
└── mcp_server/
    ├── handlers/
    │   └── graph_viewer_manager.py  # MCP интеграция
    └── server.py                    # MCP сервер
```

## 📚 Документация

См. также:
- [Библиотека graph_viewer](../lib/graph_viewer/README.md)
- [Проектная документация](../../docs/project/project-docs.json)
- [Архитектурные решения](../../docs/project/decisions/)
