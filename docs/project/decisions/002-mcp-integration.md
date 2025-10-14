# Решение 002: Интеграция инструментов через MCP-сервер

**Дата:** 2025-10-14  
**Статус:** ✅ Принято  
**Участники:** Александр, Claude (Cursor AI)

## Проблема

Проект fedoc включает несколько инструментов (визуализация графов, работа с документацией, управление правилами). 

**Ключевой вопрос:** Как распространять и использовать эти инструменты?

Варианты распространения:
1. Отдельные standalone приложения
2. Набор скриптов
3. Интеграция в MCP-сервер

**Требования:**
- Упрощение установки для пользователя
- Единообразие версий
- Минимизация дублирования кода
- Интеграция с Cursor AI (основной сценарий использования)
- Автоматическая доступность после установки MCP

## Рассмотренные варианты

### 1. Отдельные standalone приложения

**Описание:** Каждый инструмент (graph_viewer, rules_manager) - отдельное приложение в /home/alex/tools/

**Плюсы:**
- Независимое развитие каждого инструмента
- Простое использование без MCP
- Гибкость в выборе инструментов

**Минусы:**
- ❌ Нужно устанавливать каждый инструмент отдельно
- ❌ Проблемы синхронизации версий между инструментами
- ❌ Дублирование кода (общие утилиты, подключение к БД)
- ❌ Нет интеграции с Cursor AI
- ❌ Для каждого нового проекта нужно устанавливать все инструменты заново

**Пример проблемы:**
```
Пользователь создаёт новый проект:
1. git clone project
2. Отдельно установить graph_viewer
3. Отдельно установить rules_manager
4. Отдельно установить docs_generator
5. Настроить каждый инструмент
→ Много ручной работы, легко что-то забыть
```

---

### 2. Набор скриптов в проекте

**Описание:** Скрипты в папке tools/ или scripts/, запускаются напрямую

**Плюсы:**
- Простота реализации
- Гибкость
- Всё в одном репозитории

**Минусы:**
- ❌ Нет версионирования инструментов
- ❌ Сложно управлять зависимостями
- ❌ Нет единой точки входа
- ❌ Нет интеграции с Cursor AI
- ❌ Каждый скрипт нужно знать и помнить

**Пример проблемы:**
```bash
# Пользователь должен помнить команды:
./tools/visualize-graph.py --project fepro
./tools/get-rules.py --artifact DatabaseService
./tools/export-docs.py --format json
→ Много команд, сложно запомнить синтаксис
```

---

### 3. Библиотеки + MCP-сервер (ВЫБРАН)

**Описание:** Инструменты как библиотеки в src/lib/, интеграция через MCP-сервер, CLI обёртки в dev/tools/

**Плюсы:**
- ✅ Единая установка через MCP
- ✅ Автоматическая доступность всех инструментов
- ✅ Интеграция с Cursor AI через естественный язык
- ✅ Переиспользование кода (библиотеки)
- ✅ CLI доступен как альтернатива
- ✅ Единая версия всех инструментов
- ✅ Упрощённое обновление

**Минусы:**
- ⚠️ Зависимость от MCP протокола
- ⚠️ Нужно разрабатывать обработчики MCP

**Пример использования:**
```
Пользователь создаёт новый проект:
1. git clone fedoc
2. pip install -r requirements.txt
3. Настроить .cursor/mcp.json
→ Всё готово! Все инструменты доступны

Работа:
Пользователь: "Покажи граф проекта FEPRO"
Cursor AI → MCP → graph_viewer → Браузер
```

---

## Решение

**Выбрана архитектура "Библиотеки + MCP-интеграция"**

### Структура проекта:

```
fedoc/
├── src/
│   ├── lib/                        # Переиспользуемые библиотеки
│   │   ├── graph_viewer/          # Визуализация графов
│   │   ├── rules_manager/         # Управление правилами (будущее)
│   │   └── docs_generator/        # Генерация документов (будущее)
│   │
│   └── mcp_server/                # MCP-сервер fedoc
│       ├── handlers/              # Обработчики команд
│       │   ├── graph_visualizer.py   # Использует lib.graph_viewer
│       │   ├── rules_handler.py      # Использует lib.rules_manager
│       │   └── docs_handler.py       # Использует lib.docs_generator
│       └── server.py
│
└── dev/tools/                     # CLI обёртки (опционально)
    ├── view-graph.sh              # Вызывает lib.graph_viewer
    └── get-rules.sh               # Вызывает lib.rules_manager
```

### Сценарии использования:

**1. Основной сценарий (через Cursor AI):**
```
Пользователь: "Покажи граф проекта FEPRO"
    ↓
Cursor AI (распознаёт намерение)
    ↓
MCP Server (команда show_graph)
    ↓
handlers/graph_visualizer.py (вызывает lib.graph_viewer)
    ↓
lib.graph_viewer.ArangoGraphViewer (выполняет)
    ↓
Браузер (интерактивная визуализация)
```

**2. Альтернативный сценарий (CLI):**
```bash
dev/tools/view-graph.sh --project fepro
    ↓
Импортирует lib.graph_viewer
    ↓
Выполняет визуализацию
    ↓
Браузер
```

---

## Реализация

### Установка пользователем:

```bash
# Шаг 1: Клонировать проект
git clone https://github.com/bondalen/fedoc.git
cd fedoc

# Шаг 2: Установить зависимости
pip install -r requirements.txt

# Шаг 3: Настроить MCP в Cursor
# Добавить в .cursor/mcp.json:
{
  "mcpServers": {
    "fedoc": {
      "command": "python",
      "args": ["/path/to/fedoc/src/mcp_server/server.py"],
      "env": {
        "ARANGO_HOST": "http://localhost:8529",
        "ARANGO_DB": "fedoc",
        "ARANGO_PASSWORD": "..."
      }
    }
  }
}

# Готово! Все инструменты доступны через Cursor AI
```

### Разработка библиотеки (на примере graph_viewer):

```python
# src/lib/graph_viewer/viewer.py
class ArangoGraphViewer:
    """Библиотека визуализации графов ArangoDB"""
    
    def __init__(self, host, database, username, password):
        self.client = ArangoClient(hosts=host)
        self.db = self.client.db(database, username=username, password=password)
    
    def fetch_graph(self, graph_name, project_filter, start_node, depth):
        """Получить граф из ArangoDB"""
        # ...
        
    def visualize(self, edges, theme='dark'):
        """Создать интерактивную визуализацию"""
        # ...
```

### Интеграция в MCP:

```python
# src/mcp_server/handlers/graph_visualizer.py
from lib.graph_viewer import ArangoGraphViewer
from ..config import ARANGO_HOST, ARANGO_DB, ARANGO_USER, ARANGO_PASSWORD

def show_graph(project: str = None, depth: int = 5, theme: str = "dark"):
    """MCP команда для визуализации графа"""
    viewer = ArangoGraphViewer(
        host=ARANGO_HOST,
        database=ARANGO_DB,
        username=ARANGO_USER,
        password=ARANGO_PASSWORD
    )
    
    edges = viewer.fetch_graph(
        graph_name="common_project_graph",
        project_filter=project,
        start_node="canonical_nodes/c:backend",
        depth=depth
    )
    
    viewer.visualize(edges, theme=theme)
    return f"Граф проекта '{project}' открыт в браузере"
```

### CLI обёртка:

```bash
#!/bin/bash
# dev/tools/view-graph.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

python3 -m lib.graph_viewer.viewer \
    --password "$ARANGO_PASSWORD" \
    "$@"
```

---

## Последствия

### Положительные:

1. **✅ Простота установки**
   - Одна команда `pip install -r requirements.txt`
   - Автоматическая доступность всех инструментов

2. **✅ Единая версия**
   - Все инструменты синхронизированы
   - Обновление fedoc обновляет всё

3. **✅ AI-first подход**
   - Работа через естественный язык
   - Нет необходимости запоминать команды

4. **✅ Гибкость**
   - MCP для Cursor AI
   - CLI для скриптов и автоматизации
   - Программный доступ через import

5. **✅ DRY (Don't Repeat Yourself)**
   - Один код для всех способов использования
   - Упрощённое тестирование
   - Легко поддерживать

6. **✅ Переносимость**
   - Клонировал проект → всё работает
   - Не нужно устанавливать дополнительные инструменты

### Отрицательные:

1. **⚠️ Зависимость от MCP**
   - При проблемах с MCP протоколом всё недоступно
   - Митигация: CLI доступен как запасной вариант

2. **⚠️ Монолитность**
   - Все инструменты в одном пакете
   - Нельзя установить только graph_viewer
   - Митигация: Зависимости опциональны, можно использовать только нужное

3. **⚠️ Сложность разработки MCP**
   - Нужно разрабатывать обработчики для каждой функции
   - Митигация: Обработчики простые, основная логика в библиотеках

---

## Альтернативы на будущее

Если MCP не подойдёт:
1. **FastAPI обёртка** - REST API для инструментов
2. **Desktop приложение** - Electron или Tauri
3. **Standalone пакеты** - PyPI пакеты для каждого инструмента

Но на данный момент MCP-подход полностью соответствует целям проекта.

---

## Связанные решения

- [001-arangodb-choice.md](001-arangodb-choice.md) - выбор ArangoDB
- [003-graph-viewer-arch.md](003-graph-viewer-arch.md) - архитектура graph_viewer

---

## Дополнительные материалы

- [MCP Protocol](https://modelcontextprotocol.io/)
- [Cursor AI MCP Integration](https://docs.cursor.com/advanced/mcp)
- [fedoc MCP Server README](../../src/mcp_server/README.md)
- [graph_viewer README](../../src/lib/graph_viewer/README.md)

---

**Автор решения:** Александр, Claude (Cursor AI)  
**Дата создания:** 2025-10-14  
**Статус:** ✅ Принято и реализовано

