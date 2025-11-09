# fedoc multigraph — Основная проектная документация

**Версия:** 1.0.0  
**Дата:** 2025-11-08  
**Статус:** 🚧 В разработке (стадия проектирования)  
**Авторы:** Александр

---

## 📋 О проекте

**fedoc multigraph** — это новая версия системы fedoc, реализующая концепцию мультиграфа для управления архитектурными блоками и проектными дизайнами.

### Ключевые концепции

**Мультиграф** состоит из двух взаимосвязанных графов:

1. **mg_blocks** — граф строительных блоков (building blocks)
   - Переиспользуемые архитектурные компоненты
   - Технологии, паттерны, концепции
   - Универсальны для всех проектов

2. **mg_designs** — граф проектных дизайнов
   - Конкретные реализации для проектов
   - Связь дизайна с блоками (many-to-many)
   - Привязка рёбер к проектам

### Отличия от базовой версии fedoc

| Аспект | fedoc (базовый) | fedoc multigraph |
|--------|-----------------|------------------|
| **Граф** | Один общий граф | Два отдельных графа + связи |
| **Блоки** | Узлы в общем графе | Отдельный граф блоков |
| **Проекты** | Фильтр по рёбрам | Связь design → block |
| **Гибкость** | Средняя | Высокая |
| **Сложность** | Низкая | Средняя |

---

## 🎯 Цели и задачи

### Основные цели

1. **Переиспользование архитектурных решений**
   - Создание библиотеки строительных блоков
   - Быстрая сборка новых проектов из готовых блоков

2. **Гибкое управление проектами**
   - Один дизайн может использовать много блоков
   - Один блок может применяться во многих дизайнах

3. **Централизованное хранение знаний**
   - Накопление лучших практик в блоках
   - Эволюция блоков независимо от проектов

### Сценарии использования

**Основной пользователь:** Одиночный разработчик, управляющий группой проектов

**Workflow:**
```
1. Разработчик создаёт строительные блоки (Backend, Database, API Gateway)
2. Проектирует архитектуру нового проекта, связывая дизайн с блоками
3. Работает через Cursor AI + MCP для управления графом
4. Визуализирует через веб-интерфейс для обзора
5. Использует MCP для генерации документации и правил
```

---

## 🏗️ Архитектура

### Системная архитектура

```
┌──────────────────────────────────────────────────────────┐
│  Удаленный сервер (fedoc-server)                         │
│                                                           │
│  Docker Container: fedoc-multigraph (ПОСТОЯННЫЙ)         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ PostgreSQL 16 + Apache AGE                         │ │
│  │   ├─ mg_blocks (graph)                             │ │
│  │   ├─ mg_designs (graph)                            │ │
│  │   └─ mg (relational schema)                        │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ Flask Backend + Frontend (статика)                │ │
│  │   ├─ REST API (/api/*)                             │ │
│  │   ├─ WebSocket (/ws)                               │ │
│  │   └─ Static files (/, /assets/*)                   │ │
│  │                                                     │ │
│  │ Упаковка: fedoc-multigraph.pyz (Shiv)             │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                ↕ SSH Tunnel
┌──────────────────────────────────────────────────────────┐
│  Локальная машина разработчика                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Cursor AI ↔ MCP-fedoc (localhost)                 │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Браузер: http://localhost:8080                     │ │
│  │   - Визуализация мультиграфа                       │ │
│  │   - Редактирование блоков и дизайнов               │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Технологический стек

| Компонент | Технология | Версия | Обоснование |
|-----------|-----------|--------|-------------|
| **База данных** | PostgreSQL + Apache AGE | 16.10 / 1.6.0 | Графовые запросы + реляционная схема |
| **Backend** | Flask | 3.0+ | Простота, текущий стек fedoc |
| **Frontend** | Vue.js + Vite | 3.5 / 5.4 | Реактивность, текущий стек Graph Viewer |
| **Упаковка** | Shiv (Python) | latest | Единый .pyz артефакт (~30-40 MB) |
| **Развертывание** | Docker (монолит) | latest | Один контейнер, экономия ресурсов |
| **MCP** | Python | 3.10+ | Интеграция с Cursor AI |
| **Визуализация** | vis-network | latest | Интерактивные графы |

### Архитектурные решения

1. **Монолитный контейнер** вместо микросервисов
   - **Причина:** Один пользователь, ограниченные ресурсы
   - **Trade-off:** Меньше гибкости, но проще управление

2. **Flask** вместо FastAPI
   - **Причина:** Достаточно для малой нагрузки
   - **Trade-off:** Нет async, но меньше сложности

3. **Python Shiv (.pyz)** вместо Java JAR
   - **Причина:** Знакомый стек, меньше RAM, быстрый старт
   - **Trade-off:** Менее распространен, но работает отлично
   - **Подтверждение:** связка протестирована в контейнере `apache/age`; детали — в [psycopg2-shiv-test.md](../cc-preliminary/25-1108/psycopg2-shiv-test.md)

4. **Supervisor** для управления процессами
   - **Причина:** PostgreSQL + Flask в одном контейнере
   - **Trade-off:** Не Kubernetes, но достаточно

Подробнее: [Документ архитектурного решения](../cc-preliminary/25-1108/chat-session-architecture-design.md)

---

## 💾 Модель данных

### Графы Apache AGE

#### mg_blocks — Граф строительных блоков

**Вершины (block_type):**
```cypher
{
  id: graphid,           # Уникальный ID
  properties: {
    name: string,        # Название блока
    description: string, # Описание
    type: string,        # Тип: "concept", "technology", "pattern"
    metadata: {}         # Дополнительные свойства
  }
}
```

**Рёбра (block_edge):**
```cypher
{
  id: graphid,
  start_id: graphid,     # Родительский блок
  end_id: graphid,       # Дочерний блок
  properties: {
    relation_type: string, # "contains", "depends-on", "extends"
    weight: float          # Вес связи
  }
}
```

**Ограничения:**
- Primary key на `id`
- Запрет петель: `CHECK (NOT graphid_eq(start_id, end_id))`
- Двунаправленная уникальность: `UNIQUE (LEAST(start_id,end_id), GREATEST(start_id,end_id))`

#### mg_designs — Граф проектных дизайнов

**Вершины (design_node):**
```cypher
{
  id: graphid,
  properties: {
    name: string,        # Название элемента дизайна
    description: string,
    status: string,      # "draft", "active", "deprecated"
    created_at: timestamp
  }
}
```

**Рёбра (design_edge):**
```cypher
{
  id: graphid,
  start_id: graphid,
  end_id: graphid,
  properties: {
    relation_type: string, # "contains", "uses", "depends-on"
    metadata: {}
  }
}
```

**Ограничения:** Те же, что у mg_blocks

### Реляционная схема (mg)

#### mg.projects
```sql
id           serial PRIMARY KEY,
name         varchar UNIQUE NOT NULL,
description  text,
created_at   timestamptz DEFAULT now()
```

#### mg.design_to_block
```sql
design_id  graphid PRIMARY KEY → mg_designs.design_node(id),
block_id   graphid NOT NULL    → mg_blocks.block_type(id)
```

Связь many-to-many: один design может ссылаться на много блоков.

#### mg.design_edge_to_project
```sql
edge_id     graphid → mg_designs.design_edge(id),
project_id  integer → mg.projects(id),
PRIMARY KEY (edge_id, project_id)
```

Связь many-to-many: одно ребро дизайна может быть в нескольких проектах.

### Диаграмма связей

```
┌─────────────────┐         ┌─────────────────┐
│   mg_blocks     │         │   mg_designs    │
│  (graph AGE)    │         │  (graph AGE)    │
│                 │         │                 │
│ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │ block_type  │ │         │ │ design_node │ │
│ │ (vertices)  │ │◄────────┤ │ (vertices)  │ │
│ └─────────────┘ │         │ └─────────────┘ │
│       │         │         │       │         │
│       │         │         │       │         │
│ ┌─────────────┐ │         │ ┌─────────────┐ │
│ │ block_edge  │ │         │ │ design_edge │ │
│ │ (edges)     │ │         │ │ (edges)     │ │
│ └─────────────┘ │         │ └─────────────┘ │
└─────────────────┘         └─────────────────┘
        ▲                           ▲    │
        │                           │    │
        │   mg.design_to_block      │    │
        └───────────────────────────┘    │
                                         │
                                         │
                    ┌────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ mg.design_edge_to_    │
        │   project             │
        │                       │
        │ ┌───────────────────┐ │
        │ │   mg.projects     │ │
        │ └───────────────────┘ │
        └───────────────────────┘
```

Подробнее: [Database Architecture Overview](../cc-preliminary/25-1107/multigraph-architecture-overview.md)

---

## 🔌 API

### REST API Endpoints

**Blocks (строительные блоки):**
```
GET    /api/blocks              # Список всех блоков
GET    /api/blocks/:id          # Получить блок
POST   /api/blocks              # Создать блок
PUT    /api/blocks/:id          # Обновить блок
DELETE /api/blocks/:id          # Удалить блок

GET    /api/blocks/:id/children # Дочерние блоки
GET    /api/blocks/:id/graph    # Подграф от блока
```

**Designs (проектные дизайны):**
```
GET    /api/designs             # Список дизайнов
GET    /api/designs/:id         # Получить дизайн
POST   /api/designs             # Создать дизайн
PUT    /api/designs/:id         # Обновить дизайн
DELETE /api/designs/:id         # Удалить дизайн

GET    /api/designs/:id/blocks  # Связанные блоки
POST   /api/designs/:id/blocks  # Добавить блок к дизайну
DELETE /api/designs/:id/blocks/:block_id # Удалить связь
```

**Projects (проекты):**
```
GET    /api/projects            # Список проектов
GET    /api/projects/:id        # Получить проект
POST   /api/projects            # Создать проект
PUT    /api/projects/:id        # Обновить проект
DELETE /api/projects/:id        # Удалить проект

GET    /api/projects/:id/graph  # Граф проекта (дизайны + блоки)
```

### WebSocket API

**Подключение:** `ws://localhost:8080/ws`

**События (Client → Server):**
```json
{
  "type": "subscribe",
  "channel": "graph_updates"
}

{
  "type": "get_selected_nodes"
}
```

**События (Server → Client):**
```json
{
  "type": "graph_updated",
  "data": {
    "entity_type": "block",
    "entity_id": "123",
    "action": "created"
  }
}

{
  "type": "selected_nodes",
  "data": {
    "nodes": ["id1", "id2"],
    "edges": ["edge1"]
  }
}
```

---

## 🔧 MCP Integration

### MCP Commands

**Работа с блоками:**
```python
# Создать блок
mcp.call("create_block", {
    "name": "API Gateway",
    "type": "technology",
    "description": "..."
})

# Получить дочерние блоки
mcp.call("get_block_children", {
    "block_id": "123"
})
```

**Работа с дизайнами:**
```python
# Создать дизайн
mcp.call("create_design", {
    "name": "User Service Architecture",
    "project_id": 1
})

# Связать дизайн с блоком
mcp.call("link_design_to_block", {
    "design_id": "456",
    "block_id": "123"
})
```

**Визуализация:**
```python
# Открыть веб-интерфейс
mcp.call("open_graph_viewer", {
    "project_id": 1
})

# Получить выделенные элементы из браузера
selected = mcp.call("get_selected_elements")
```

---

## 📦 Развертывание

Backend multigraph развёртывается в монолитном контейнере вместе с PostgreSQL + Apache AGE и управляется Supervisor. Подробные инструкции по сборке образа, первичному развёртыванию, обновлению `.pyz` и откату приведены в [ab-project-backend.md](ab-project-backend.md#📦-развертывание).

Ключевые принципы на уровне проекта:
- один контейнер, `bind`-монтаж `/app` для размещения `.pyz`;
- обновления выполняются заменой артефакта и рестартом приложения (БД не перезапускается);
- сервис доступен только через SSH tunnel, внешние порты не публикуются.

---

## 🛠️ Разработка

Внутренняя структура каталога `mgsrc/`, сценарии локальной разработки и процесс сборки `.pyz` описаны в [ab-project-backend.md](ab-project-backend.md#🛠️-разработка). На уровне проекта важно помнить, что backend публикует REST и WebSocket интерфейсы, а фронтенд и MCP используют их через единый `.pyz` артефакт. При изменениях интерфейсов обновляйте соответствующие разделы API в текущем документе.

---

## 📊 Мониторинг и логи

Операционные команды для проверки состояния контейнера, чтения логов и наблюдения за ресурсами собраны в [ab-project-backend.md](ab-project-backend.md#📊-мониторинг-и-логи). На проектном уровне необходимо обеспечивать доступ к `docker stats`, `supervisorctl status` и журналам приложений для быстрой диагностики инцидентов.

---

## 🔐 Безопасность

Актуальная модель безопасности backend, действующие ограничения и план по усилению защиты приведены в [ab-project-backend.md](ab-project-backend.md#🔐-безопасность). Важно: сервис рассчитан на одного пользователя, внешние порты не публикуются, доступ осуществляется исключительно через SSH tunnel; расширение модели (JWT, RBAC, HTTPS) запланировано для будущего мультипользовательского режима.

---

## 📚 Документация

### Основная документация (aa-main-docs/)
- **aa-project.md** (этот документ) — Обзор проекта
- [ab-project-backend.md](ab-project-backend.md) — Внутренняя документация backend

### Резюме чатов (bb-chats/)
- [chat-25-1107-resume-16-37.md](../bb-chats/chat-25-1107-resume-16-37.md) — Создание БД
- [chat-25-1108-resume-10-55.md](../bb-chats/chat-25-1108-resume-10-55.md) — Определение архитектуры
- [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md) — Каркас backend и окружение

### Предварительные материалы (cc-preliminary/)
- [25-1107/multigraph-architecture-overview.md](../cc-preliminary/25-1107/multigraph-architecture-overview.md) — Детали БД
- [25-1108/chat-session-architecture-design.md](../cc-preliminary/25-1108/chat-session-architecture-design.md) — Архитектурное решение

---

## 🚀 Roadmap

### Milestone 1: MVP Backend (в процессе)
- [x] Структура проекта mgsrc/
- [x] Flask app с базовым API (health endpoint)
- [ ] Подключение к PostgreSQL
- [ ] Dockerfile + Supervisor
- [ ] Скрипт build-pyz.sh
- [ ] Один working endpoint: POST /api/blocks

**Срок:** 1-2 недели

### Milestone 2: MVP Frontend
- [ ] Vue 3 проект
- [ ] Базовая визуализация графа (vis-network)
- [ ] Интеграция с backend API
- [ ] Сборка в backend/static/

**Срок:** 1-2 недели

### Milestone 3: MCP Integration
- [ ] MCP server базовый
- [ ] Handlers для блоков и дизайнов
- [ ] WebSocket для двусторонней связи
- [ ] Тестирование в Cursor AI

**Срок:** 1 неделя

### Milestone 4: Развертывание
- [ ] Скрипты deploy/update/rollback
- [ ] Развертывание на fedoc-server
- [ ] Smoke tests
- [ ] Документация

**Срок:** 1 неделя

### Future (после MVP)
- [ ] Импорт существующих данных из fedoc
- [ ] Расширенная визуализация
- [ ] Экспорт в различные форматы
- [ ] Шаблоны и паттерны
- [ ] Версионирование блоков

---

## 🤝 Контрибьютинг

**Текущий статус:** Проект в стадии разработки, одиночный разработчик

**Если потребуется:**
1. Fork репозиторий
2. Создать feature branch
3. Commit изменений
4. Push в branch
5. Создать Pull Request

---

## 📄 Лицензия

Apache License 2.0 (аналогично основному проекту fedoc)

---

## 📞 Контакты

**Автор:** Александр  
**Репозиторий:** https://github.com/bondalen/fedoc (ветка multigraph)  
**Проект:** fedoc - Централизованная система правил и документации

---

## ✅ Тестирование и CI

### Локальные проверки
- `pytest -m integration` — основной прогон, требует доступной PostgreSQL/AGE и переменной `FEDOC_DATABASE_URL`.
- `python -m fedoc_multigraph.scripts.seed_multigraph --force` — приводит БД к известному состоянию (блоки, дизайны, демонстрационный проект с ребром).
- На 2025-11-09 проходит 16 интеграционных тестов, включая негативные сценарии для `/api/projects`.

### GitHub Actions
- Workflow `.github/workflows/integration-tests.yml` запускается на `push`/`pull_request` в `main`.
- Шаги:
  1. Развёртывание `apache/age:latest` с БД `fedoc`.
  2. Инициализация AGE: `CREATE EXTENSION`, `create_graph`, `create_vlabel`, таблица `mg.design_to_block`.
  3. Установка зависимостей и запуск `pytest -m integration` с `FEDOC_DATABASE_URL` из секретов.

### Покрытие
- `/api/blocks` — CRUD + негативные (`404`, `422`).
- `/api/designs` — CRUD, связи `block_id`, негативные (`404`, `409`, `422`).
- `/api/projects` — CRUD, управление `design_edge_to_project`, граф (`designs`, `edges`, `blocks`), устойчивость к удалённым рёбрам.

**Последнее обновление:** 2025-11-09  
**Версия документа:** 1.0.0

