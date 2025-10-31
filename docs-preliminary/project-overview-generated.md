# Проект FEDOC

## Метаинформация
- **Назначение**: Централизованная система правил и проектной документации для группы проектов
- **Статус**: active
- **Версия**: 0.1.0
- **Автор**: Александр

## Технологический стек

### Основные технологии
- **Язык бэкенда**: Python 3.12
- **База данных**: PostgreSQL 16 + Apache AGE (графовое расширение)
- **Фронтенд**: Vue.js 3 + Vite 5
- **API**: REST (Flask)
- **Визуализация графа**: vis-network, Socket.IO
- **MCP-сервер**: Python 3.10+, Flask-SocketIO, psycopg2
- **AI-IDE**: Cursor (использует MCP-протокол)

## Архитектура проекта

### Основные компоненты

#### 1. MCP-сервер fedoc (`t:mcp-fedoc`)
- Реализует Model Context Protocol для интеграции с Cursor AI
- Предоставляет команды для работы с графом (создание, обновление, удаление узлов/рёбер)
- **Использует REST API** бэкенда для доступа к данным
- Стек: Python 3.10+, Flask-SocketIO, psycopg2, python-arango
- Порт: 15000

#### 2. Graph Viewer (`t:graph_viewer`)
- Веб-приложение для визуализации технологического графа
- **Использует REST API** бэкенда для загрузки данных
- Стек: Vue 3, Vite 5, vis-network, Socket.IO
- Порт: 5173

#### 3. Backend API
- Flask-сервер, предоставляющий REST API
- Работает с PostgreSQL + Apache AGE
- Обслуживает и MCP-сервер, и Graph Viewer

### Цикл в графе

Проект содержит **цикл** на уровне архитектуры:

```
c:layer (Слой)
  ├─[includes]→ c:frontend (Фронтенд)
  │                └─[uses]→ t:rest (REST API)
  │                             ↑
  │                             |
  │                      [implementedBy]
  │                             |
  └─[includes]→ c:backend ─[provides]→ c:backend-api
                                              ↑
                                              |
                                      [implementedBy]
                                              └──────────┘
```

**Семантика цикла**:
- Слой включает фронтенд и бэкенд
- Фронтенд использует REST API
- REST реализует API бэкенда
- API предоставляется бэкендом
- Бэкенд — часть того же слоя

Это типичная клиент-серверная архитектура, где фронтенд и бэкенд взаимодействуют через REST.

## Принципы разработки

### dev-001: Структурная нумерация 01-zz
**Утверждение**: Все структурные элементы проекта (модули, компоненты, классы, задачи) нумеруются по системе 01-zz, обеспечивающей 1295 позиций на уровень иерархии.

**Правила**:
- Формат: два символа 01-99, 0a-9z, a0-z9, aa-zz
- Иерархия: через точку (например, 01.02.0a)
- Резерв: 00 зарезервирован для специальных целей
- Ёмкость: 1295 уникальных ID на уровень

**Обоснование**: Компактная и расширяемая система нумерации, избегающая конфликтов при росте проекта.

**Применимость**: модули, компоненты, классы, задачи, деревья структур

---

### dev-002: Инструменты как библиотеки (DRY)
**Утверждение**: Все инструменты разрабатываются как переиспользуемые библиотеки в `src/lib/`, интегрируются в MCP и доступны через CLI.

**Преимущества**:
- Один код для MCP и CLI
- Упрощённое тестирование
- Единая версия инструмента

**Структура**:
- `src/lib/` — библиотеки
- `src/mcp_server/handlers/` — интеграция в MCP
- `dev/tools/` — CLI-обёртки

**Пример**: graph_viewer используется из MCP (`handlers/graph_visualizer.py`) и CLI (`dev/tools/view-graph.sh`)

---

### dev-003: Граф как первичная структура данных
**Утверждение**: Связи между элементами представляются в виде направленного ацикличного графа (DAG) в базе данных.

**Реализация**:
- БД: Apache AGE (графовое расширение PostgreSQL)
- Коллекции: `canonical_nodes`, `project_edges`
- Граф: `common_project_graph`
- DAG-структура: элемент может иметь несколько родителей (пример: задача в нескольких деревьях)

**Обоснование**:
- Естественное представление зависимостей
- Множественные пути к элементу для сбора правил
- Визуализация сложных связей

---

### dev-004: Документация как код
**Утверждение**: Проектная документация хранится в структурированном формате (JSON) в базе данных для программной обработки.

**Форматы**:
- `project-docs.json` — архитектура
- `project-development.json` — планирование (DAG задач)
- `project-journal.json` — журнал разработки

**Хранение**: PostgreSQL коллекции
**Валидация**: pydantic-схемы

**Обоснование**:
- Валидация и проверка целостности
- Программный доступ к данным
- Автоматическая генерация производных документов

## Системные принципы

### sys-001: Сборка документации через обход графа
**Утверждение**: При обходе общего графа проектов по рёбрам, которым присвоен ключ проекта, собирается полный комплект проектной документации и правил проекта.

**Применимость**: query, export, validation

---

### sys-002: Контекстная сборка правил для артефакта
**Утверждение**: При переходе от артефакта (класс, модуль, задача) к связанному элементу общего графа и подъёме к корню проекта собирается полный комплект правил для работы над этим артефактом.

**Пример**: Для класса DatabaseService: Class → Component → Module → Project (собираются все применимые правила)

---

### sys-003: Интерактивное создание проекта через MCP
**Утверждение**: При создании нового проекта достаточно установить MCP-сервер и получить доступ к БД, чтобы с AI-ассистентом в режиме вопрос-ответ создать полный комплект документации.

**Применимость**: project-creation, onboarding, scaffolding

---

### sys-004: Автоматическая доступность инструментов через MCP
**Утверждение**: После установки MCP-сервера все инструменты проекта (визуализация, запросы, управление) доступны автоматически без дополнительных установок.

**Реализация**: Инструменты как библиотеки в `src/lib/`, интеграция через `src/mcp_server/handlers/`

---

### sys-005: Централизация знаний в единой базе
**Утверждение**: Вся проектная документация, правила и наработки хранятся в единой базе данных PostgreSQL+AGE, доступной всем проектам группы.

---

### sys-006: AI-first подход к взаимодействию
**Утверждение**: Основной способ работы с системой — через AI-ассистент (Cursor AI) с использованием естественного языка.

**Реализация**: MCP-сервер как интерфейс для Cursor AI, CLI как резервный вариант

---

## Граф зависимостей (JSON, DAG)

```json
{
  "nodes": {
    "c:project": {"name": "Проект", "kind": "concept"},
    "c:dev-objects": {"name": "Объекты разработки", "kind": "concept"},
    "c:mcp": {"name": "MCP-сервер", "kind": "concept"},
    "t:mcp-fedoc": {"name": "MCP-сервер fedoc", "kind": "technology"},
    "c:application": {"name": "Приложение", "kind": "concept"},
    "c:web-app": {"name": "Веб-приложение", "kind": "concept"},
    "t:graph_viewer": {"name": "Graph Viewer", "kind": "technology"},
    "c:layer": {"name": "Слой", "kind": "concept"},
    "c:frontend": {"name": "Фронтенд", "kind": "concept"},
    "c:frontend-framework": {"name": "Фронтенд-фреймворк", "kind": "concept"},
    "t:vue": {"name": "Vue.js", "kind": "technology"},
    "t:vite": {"name": "Vite", "kind": "technology"},
    "c:backend": {"name": "Бэкенд", "kind": "concept"},
    "c:backend-api": {"name": "API бакенда", "kind": "concept"},
    "c:backend-main-language": {"name": "Основной язык бакенда", "kind": "concept"},
    "t:python": {"name": "Python", "kind": "technology"},
    "v:python@3.12": {"name": "Python 3.12", "kind": "version"},
    "c:backend-database": {"name": "БД бэкенда", "kind": "concept"},
    "t:postgresql@16": {"name": "PostgreSQL", "kind": "technology"},
    "t:rest": {"name": "REST", "kind": "technology"},
    "c:ai-ide": {"name": "AI-интегрированная IDE", "kind": "concept"},
    "t:cursor": {"name": "Cursor", "kind": "technology"}
  },
  "edges": [
    {"from": "c:project", "to": "c:dev-objects", "type": "contains"},
    {"from": "c:dev-objects", "to": "c:mcp", "type": "includes"},
    {"from": "c:dev-objects", "to": "c:application"},
    {"from": "c:mcp", "to": "t:mcp-fedoc", "type": "implementedBy"},
    {"from": "t:mcp-fedoc", "to": "t:rest", "type": "uses"},
    {"from": "c:application", "to": "c:web-app"},
    {"from": "c:web-app", "to": "t:graph_viewer", "type": "implementedBy"},
    {"from": "t:graph_viewer", "to": "c:layer", "type": "uses"},
    {"from": "c:layer", "to": "c:frontend", "type": "includes"},
    {"from": "c:layer", "to": "c:backend", "type": "includes"},
    {"from": "c:frontend", "to": "c:frontend-framework", "type": "uses"},
    {"from": "c:frontend", "to": "t:rest", "type": "uses"},
    {"from": "c:frontend-framework", "to": "t:vue", "type": "implementedBy"},
    {"from": "t:vue", "to": "t:vite", "type": "uses"},
    {"from": "c:backend", "to": "c:backend-api", "type": "provides"},
    {"from": "c:backend", "to": "c:backend-main-language"},
    {"from": "c:backend", "to": "c:backend-database"},
    {"from": "c:backend-api", "to": "t:rest", "type": "implementedBy"},
    {"from": "c:backend-main-language", "to": "t:python", "type": "includes"},
    {"from": "t:python", "to": "v:python@3.12", "type": "includes"},
    {"from": "c:backend-database", "to": "t:postgresql@16", "type": "uses"},
    {"from": "c:ai-ide", "to": "t:cursor", "type": "implementedBy"},
    {"from": "t:cursor", "to": "c:mcp", "type": "uses"}
  ]
}
```

---

## Выводы

Проект FEDOC представляет собой **сложный DAG** с циклами на архитектурном уровне. Ключевые характеристики:

1. **Цикл**: Frontend → REST ← Backend → Layer → Frontend (клиент-серверная архитектура)
2. **Множественные пути**: REST используется и фронтендом, и MCP-сервером
3. **Иерархическая структура**: Проект → Объекты разработки → Приложения → Слои → Компоненты
4. **AI-first**: Cursor (через MCP) → MCP-сервер → REST API → PostgreSQL+AGE

Для LLM оптимален **гибридный формат**: Markdown (описания, принципы) + JSON (граф с явными связями).
