# Скрипты инициализации PostgreSQL для fedoc

## Миграция на PostgreSQL + Apache AGE

Эта директория содержит SQL скрипты для инициализации PostgreSQL с Apache AGE для проекта fedoc.

### Скрипты выполняются автоматически при создании контейнера

Порядок выполнения (по номерам файлов):

1. **01-init-age.sql** - Создание базы данных `fedoc`
2. **02-setup-age-extension.sql** - Установка расширения Apache AGE
3. **03-create-graph.sql** - Создание графа `common_project_graph`
4. **04-validation-functions.sql** - Функции валидации рёбер (ключевая фича!)
5. **05-create-schema.sql** - Создание схемы (метки вершин и рёбер)

### Ключевая фича миграции

**Функции валидации в PostgreSQL** (файл 04):
- `check_edge_uniqueness()` - проверка уникальности связи в обоих направлениях
- `create_edge_safe()` - атомарное создание ребра с валидацией
- `update_edge_safe()` - обновление ребра с валидацией
- `delete_edge_safe()` - безопасное удаление ребра

**Преимущества:**
- ✅ Вся логика валидации в БД (не в приложении)
- ✅ Атомарность (проверка + создание в одной транзакции)
- ✅ Один вызов функции вместо двух запросов
- ✅ Упрощение кода приложения

### Миграция данных

После инициализации базы данных необходимо:

1. Экспортировать данные из ArangoDB
2. Запустить скрипт миграции (см. `scripts/migrate-arango-to-age.py`)
3. Проверить данные

### Проверка установки

```bash
# На сервере
ssh vuege-server "docker exec fedoc-postgres psql -U postgres -d fedoc -c \"SELECT * FROM ag_catalog.ag_graph;\""

# Проверить функции
ssh vuege-server "docker exec fedoc-postgres psql -U postgres -d fedoc -c \"\df check_edge_uniqueness\""
```

### Версии

- PostgreSQL: 16.10
- Apache AGE: 1.6.0
- Сервер: 176.108.244.252

---

**Дата создания:** 18 октября 2025  
**Автор:** Александр
