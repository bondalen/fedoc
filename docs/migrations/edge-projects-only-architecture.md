# Архитектура хранения проектов в рёбрах: edge_projects таблица

**Дата создания:** 2025-11-03  
**Статус:** ✅ Реализовано  
**Версия:** 3.0

## 📋 Обзор

Все связи рёбер с проектами теперь хранятся **исключительно** в нормализованной таблице `public.edge_projects`. Поле `projects` больше не используется в свойствах рёбер Apache AGE графа.

## 🏗️ Архитектура

### Таблица edge_projects

```sql
CREATE TABLE public.edge_projects (
    id SERIAL PRIMARY KEY,
    edge_id BIGINT NOT NULL,                    -- ID ребра в Apache AGE
    project_id INTEGER REFERENCES public.projects(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'participant',     -- Роль проекта в связи
    weight DECIMAL(3,2) DEFAULT 1.0,            -- Вес связи (0.0-1.0)
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',   -- Кто создал связь
    metadata JSONB DEFAULT '{}'::JSONB,        -- Дополнительные метаданные
    UNIQUE(edge_id, project_id)                 -- Предотвращение дубликатов
);
```

### Преимущества

- ✅ **Целостность данных**: Foreign Key на `projects.id`
- ✅ **Защита от дубликатов**: `UNIQUE(edge_id, project_id)`
- ✅ **Производительность**: Индексы для быстрых JOIN
- ✅ **Расширяемость**: Поля role, weight, metadata
- ✅ **Быстрые запросы**: JOIN вместо JSON-поиска

## 📂 Изменённые компоненты

### 1. Функции Graph Viewer

**Файл:** `dev/docker/init-scripts/postgres/06-graph-viewer-functions.sql`

Все функции теперь используют JOIN с `edge_projects`:
- `get_all_graph_for_viewer()` - фильтрация через EXISTS с edge_projects
- `get_graph_for_viewer()` - фильтрация через EXISTS с edge_projects  
- `get_all_nodes_for_viewer()` - фильтрация через связанные рёбра
- `expand_node_for_viewer()` - фильтрация через EXISTS с edge_projects

**Вспомогательная функция:**
- `get_edge_projects_array(edge_id)` - возвращает массив ключей проектов для ребра

### 2. Edge Validator

**Файл:** `src/lib/graph_viewer/backend/edge_validator_age.py`

Автоматическая синхронизация при создании/обновлении рёбер:

- `insert_edge_safely()` - извлекает `projects` из properties, сохраняет в `edge_projects`
- `update_edge_safely()` - синхронизирует `projects` в таблице
- `delete_edge()` - удаляет связанные записи из `edge_projects`

### 3. Project Enricher

**Файл:** `src/lib/graph_viewer/backend/project_enricher.py`

Приоритет чтения:
1. **ПРИОРИТЕТ**: `edge_projects` таблица (если есть `edge_id`)
2. **FALLBACK**: `properties.projects` (для старых данных, обратная совместимость)

## 🚀 Миграция

### Шаг 1: Миграция данных

```bash
python scripts/migrate_all_projects_to_table.py \
    <host> <port> <database> <user> <password>
```

**Что делает:**
- Находит все рёбра с `e.projects` в графе
- Добавляет их в `edge_projects` через `add_project_to_edge()`
- Идемпотентный: пропускает уже существующие записи

### Шаг 2: Проверка целостности

```bash
python scripts/verify_edge_projects_integrity.py \
    <host> <port> <database> <user> <password>
```

**Проверяет:**
- Все рёбра с `e.projects` есть в `edge_projects`
- Нет дубликатов в таблице
- Все `project_id` валидны
- Все `edge_id` существуют в графе

### Шаг 3: Обновление функций Graph Viewer

```bash
psql -h <host> -p <port> -U <user> -d <database> \
    -f dev/docker/init-scripts/postgres/06-graph-viewer-functions.sql
```

### Шаг 4: Удаление projects из рёбер (финальный шаг)

**⚠️ ВНИМАНИЕ:** Выполнять только после успешной проверки целостности!

```bash
psql -h <host> -p <port> -U <user> -d <database> \
    -f scripts/remove_projects_from_edges.sql
```

## 🔄 API изменения

### Создание/обновление рёбер

API остаётся без изменений, но теперь `projects` автоматически сохраняются в `edge_projects`:

```json
POST /api/edges
{
    "_from": "canonical_nodes/c:backend",
    "_to": "canonical_nodes/t:java@21",
    "relationType": "uses",
    "projects": ["fepro", "femsq"]
}
```

**Что происходит:**
1. Ребро создаётся в графе **БЕЗ** поля `projects`
2. Проекты автоматически добавляются в `edge_projects`

### Получение рёбер

Проекты возвращаются из `edge_projects` через функции Graph Viewer или `project_enricher`.

## 📊 Функции PostgreSQL

### get_edge_projects_enriched(edge_id)

Возвращает проекты ребра с полной информацией:

```sql
SELECT * FROM ag_catalog.get_edge_projects_enriched(123);
```

### add_project_to_edge(edge_id, project_key, ...)

Добавить проект к ребру:

```sql
SELECT ag_catalog.add_project_to_edge(123, 'fepro', 'participant', 1.0);
```

### remove_project_from_edge(edge_id, project_key)

Удалить проект из ребра:

```sql
SELECT ag_catalog.remove_project_from_edge(123, 'fepro');
```

### get_project_edges(project_key)

Получить все рёбра проекта:

```sql
SELECT * FROM ag_catalog.get_project_edges('fepro');
```

## ⚠️ Важные замечания

1. **Обратная совместимость**: Старые данные с `properties.projects` поддерживаются через fallback в `project_enricher.py`

2. **Автоматическая синхронизация**: Все новые рёбра автоматически синхронизируются с `edge_projects`

3. **Производительность**: JOIN с индексами значительно быстрее JSON-поиска в Apache AGE

4. **Целостность**: Foreign Keys и UNIQUE ограничения предотвращают ошибки

## 🔍 Проверка состояния

### Количество рёбер с проектами

```sql
-- В графе (старый формат)
SELECT COUNT(*) 
FROM ag_edge e
WHERE agtype_to_json(e.properties)::jsonb ? 'projects';

-- В таблице (новый формат)
SELECT COUNT(DISTINCT edge_id) 
FROM public.edge_projects;
```

### Статистика по проектам

```sql
SELECT 
    p.key as project_key,
    COUNT(*) as edge_count
FROM public.edge_projects ep
JOIN public.projects p ON ep.project_id = p.id
GROUP BY p.key
ORDER BY edge_count DESC;
```

## 📝 История изменений

- **2025-11-03**: Полная миграция на `edge_projects` как единственный источник истины
- **2025-10-26**: Создание нормализованной структуры `edge_projects`
- **2025-10-14**: Первоначальная реализация с массивом `projects` в свойствах

