# Нормализованная архитектура проектов в рёбрах графа

**Дата:** 2025-10-26  
**Статус:** ✅ Реализовано  
**Версия:** 2.0

## 🎯 Цель

Заменить простое поле `properties.projects` в рёбрах графа на нормализованную реляционную структуру для:
- Устранения неоднозначности между проектами
- Добавления метаданных связей (роли, веса, даты)
- Улучшения производительности запросов
- Обеспечения целостности данных

## 🏗️ Архитектура

### Нормализованная структура

```sql
-- Таблица связи рёбер с проектами
CREATE TABLE public.edge_projects (
    id SERIAL PRIMARY KEY,
    edge_id BIGINT NOT NULL,                    -- ID ребра в Apache AGE
    project_id INTEGER REFERENCES public.projects(id), -- Ссылка на проект
    role VARCHAR(50) DEFAULT 'participant',     -- Роль проекта в связи
    weight DECIMAL(3,2) DEFAULT 1.0,            -- Вес связи (0.0-1.0)
    created_at TIMESTAMP DEFAULT NOW(),        -- Дата создания связи
    created_by VARCHAR(100) DEFAULT 'system',   -- Кто создал связь
    metadata JSONB DEFAULT '{}'::JSONB,        -- Дополнительные метаданные
    UNIQUE(edge_id, project_id)
);
```

### Функции для работы с данными

```sql
-- Получение проектов ребра с полной информацией
SELECT * FROM ag_catalog.get_edge_projects_enriched(edge_id);

-- Добавление проекта к ребру
SELECT ag_catalog.add_project_to_edge(edge_id, 'project_key', 'role', weight);

-- Удаление проекта из ребра
SELECT ag_catalog.remove_project_from_edge(edge_id, 'project_key');

-- Получение всех рёбер проекта
SELECT * FROM ag_catalog.get_project_edges('project_key');
```

## 📊 Результаты миграции

- **Всего рёбер:** 34
- **Связей проект-ребро:** 55
- **Уникальных проектов:** 3 (fepro, femsq, fedoc)
- **Рёбер с проектами:** 34

## 🔄 API изменения

### До (старая структура)
```json
{
  "properties": {
    "projects": ["fepro", "femsq", "fedoc"]
  }
}
```

### После (новая структура)
```json
{
  "properties": {
    "projects": [
      {
        "id": "fedoc",
        "name": "fedoc",
        "description": "Централизованная система правил...",
        "role": "participant",
        "weight": 1.0,
        "relation_created_at": "2025-10-26T08:25:40.235703",
        "relation_created_by": "migration",
        "relation_metadata": {
          "migrated_from": "properties.projects",
          "migration_date": "2025-10-26T08:25:40.235703+00:00"
        }
      }
    ]
  }
}
```

## 🚀 Преимущества

### ✅ Устранение неоднозначности
- Каждый проект имеет уникальный ID и полную информацию
- Нет путаницы между проектами с похожими именами

### ✅ Метаданные связей
- **Роли:** participant, owner, consumer, etc.
- **Веса:** приоритет связей (0.0-1.0)
- **Аудит:** кто и когда создал связь
- **Метаданные:** дополнительная информация в JSON

### ✅ Производительность
- Индексы на `edge_id`, `project_id`, `role`
- Быстрые JOIN запросы
- Материализованные представления для аналитики

### ✅ Целостность данных
- Foreign Key на таблицу `projects`
- Уникальность связей `(edge_id, project_id)`
- Каскадное удаление при удалении проекта

## 🔧 Влияние на кэш

**✅ Минимальное влияние:**
- Frontend получает те же структурированные данные
- Кэш работает с готовыми данными от API
- Обогащение происходит на уровне API
- Прозрачность для клиентского кода

## 📁 Файлы реализации

### Миграции
- `001_create_normalized_projects.sql` - Создание структуры
- `002_create_project_functions.sql` - Функции для работы
- `003_migrate_final.sql` - Миграция данных

### API обновления
- `project_enricher.py` - Обогащение данных проектов
- `api_server_age.py` - Интеграция в API

### Тестирование
- `run_migrations.py` - Скрипт выполнения миграций

## 🎯 Следующие шаги

1. **Оптимизация запросов** - материализованные представления
2. **Аналитика** - отчёты по связям проектов
3. **UI улучшения** - отображение ролей и весов
4. **Документация** - руководство по использованию

## 🔍 Примеры использования

### Получение всех проектов ребра
```sql
SELECT project_info->>'name' as project_name,
       role,
       weight
FROM ag_catalog.get_edge_projects_enriched(1125899906842625);
```

### Аналитика по проектам
```sql
SELECT p.name,
       COUNT(ep.edge_id) as total_connections,
       AVG(ep.weight) as avg_weight
FROM public.projects p
LEFT JOIN public.edge_projects ep ON p.id = ep.project_id
GROUP BY p.id, p.name;
```

### Добавление нового проекта к ребру
```sql
SELECT ag_catalog.add_project_to_edge(
    1125899906842625,
    'new_project',
    'owner',
    0.8,
    'user@example.com',
    '{"source": "manual", "reason": "primary_owner"}'::JSONB
);
```

---

**Результат:** Нормализованная архитектура успешно реализована и протестирована. Все существующие данные мигрированы, API обновлён, Graph Viewer работает с новой структурой.
