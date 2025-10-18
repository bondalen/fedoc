# Руководство по миграции fedoc на PostgreSQL + Apache AGE

**Дата:** 18 октября 2025  
**Автор:** Александр

---

## 📋 Подготовка

### 1. Проверка версий (✅ выполнено)

- PostgreSQL: 16.10
- Apache AGE: 1.6.0  
- Сервер: 176.108.244.252

### 2. Бэкап текущих данных ArangoDB

```bash
# На сервере
ssh vuege-server

# Создать директорию для бэкапов
mkdir -p ~/backups/fedoc-arango-$(date +%Y%m%d)

# Экспорт данных (через arangodump внутри контейнера)
docker exec fedoc-arango arangodump \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username root \
  --server.password "your_password" \
  --server.database fedoc \
  --output-directory /tmp/fedoc-backup

# Скопировать бэкап из контейнера
docker cp fedoc-arango:/tmp/fedoc-backup ~/backups/fedoc-arango-$(date +%Y%m%d)/

# Скачать на локальную машину (опционально)
scp -r vuege-server:~/backups/fedoc-arango-* ./backups/
```

---

## 🚀 Миграция

### Шаг 1: Пересоздать контейнер PostgreSQL

```bash
# На локальной машине
cd /home/alex/fedoc

# Закоммитить изменения
git add .
git commit -m "feat: add PostgreSQL + AGE migration scripts"

# Отправить на сервер
git push origin feature/migrate-to-postgresql-age

# На сервере
ssh vuege-server
cd ~/fedoc
git fetch
git checkout feature/migrate-to-postgresql-age
git pull

# Остановить и удалить старый контейнер PostgreSQL
cd dev/docker
./db-manager.sh stop-postgres
docker rm fedoc-postgres

# Удалить старые данные PostgreSQL (будет пересоздано)
rm -rf postgres-data/*

# Запустить PostgreSQL заново (скрипты инициализации выполнятся автоматически)
./db-manager.sh start-postgres
```

### Шаг 2: Проверить инициализацию

```bash
# Проверить что база fedoc создана
docker exec fedoc-postgres psql -U postgres -c "\l" | grep fedoc

# Проверить что расширение AGE установлено
docker exec fedoc-postgres psql -U postgres -d fedoc -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'age';"

# Проверить что граф создан
docker exec fedoc-postgres psql -U postgres -d fedoc -c "SET search_path = ag_catalog, public; SELECT * FROM ag_graph;"

# Проверить функции валидации
docker exec fedoc-postgres psql -U postgres -d fedoc -c "\df check_edge_uniqueness"
docker exec fedoc-postgres psql -U postgres -d fedoc -c "\df create_edge_safe"
```

**Ожидаемые результаты:**
- База данных `fedoc` существует
- Расширение `age` версии 1.6.0 установлено
- Граф `common_project_graph` создан
- Функции `check_edge_uniqueness`, `create_edge_safe`, `update_edge_safe`, `delete_edge_safe` существуют

### Шаг 3: Запустить миграцию данных

```bash
# На локальной машине (через SSH туннель)

# Установить зависимости
pip install -r scripts/migration-requirements.txt

# Создать SSH туннели для обеих БД
ssh -L 8529:localhost:8529 vuege-server -N &  # ArangoDB
ssh -L 5432:localhost:5432 vuege-server -N &  # PostgreSQL

# Запустить миграцию
python3 scripts/migrate-arango-to-age.py \
  --arango-host http://localhost:8529 \
  --arango-db fedoc \
  --arango-user root \
  --arango-password "your_arango_password" \
  --pg-host localhost \
  --pg-port 5432 \
  --pg-db fedoc \
  --pg-user postgres \
  --pg-password "your_postgres_password" \
  --graph-name common_project_graph \
  --export-mapping ./migration-id-mapping.json

# Закрыть SSH туннели
killall ssh
```

### Шаг 4: Проверить результаты миграции

```bash
# На сервере
ssh vuege-server
docker exec fedoc-postgres psql -U postgres -d fedoc

# В psql:
SET search_path = ag_catalog, public;

-- Подсчёт вершин
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n)
    RETURN count(n) as total_vertices
$$) as (total_vertices agtype);

-- Подсчёт рёбер
SELECT * FROM cypher('common_project_graph', $$
    MATCH ()-[e]->()
    RETURN count(e) as total_edges
$$) as (total_edges agtype);

-- Примеры вершин
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n:canonical_node)
    RETURN n
    LIMIT 5
$$) as (n agtype);

-- Примеры рёбер
SELECT * FROM cypher('common_project_graph', $$
    MATCH (a)-[e:project_relation]->(b)
    RETURN a.arango_key, e.projects, b.arango_key
    LIMIT 5
$$) as (from_key agtype, projects agtype, to_key agtype);
```

---

## 🧪 Тестирование

### Тест 1: Функция проверки уникальности

```sql
SET search_path = ag_catalog, public;

-- Получить ID двух вершин для теста
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n:canonical_node)
    RETURN id(n) as vertex_id, n.arango_key
    LIMIT 2
$$) as (vertex_id agtype, arango_key agtype);

-- Проверить уникальность (должно быть true)
SELECT * FROM check_edge_uniqueness(
    'common_project_graph',
    <vertex_id_1>,
    <vertex_id_2>
);
```

### Тест 2: Создание ребра с валидацией

```sql
-- Создать ребро
SELECT * FROM create_edge_safe(
    'common_project_graph',
    <vertex_id_1>,
    <vertex_id_2>,
    'project_relation',
    '{"projects": ["test"], "relationType": "test_relation"}'::jsonb
);

-- Попытаться создать дубликат (должна быть ошибка)
SELECT * FROM create_edge_safe(
    'common_project_graph',
    <vertex_id_1>,
    <vertex_id_2>,
    'project_relation',
    '{"projects": ["test2"]}'::jsonb
);

-- Попытаться создать обратную связь (должна быть ошибка)
SELECT * FROM create_edge_safe(
    'common_project_graph',
    <vertex_id_2>,
    <vertex_id_1>,
    'project_relation',
    '{"projects": ["test3"]}'::jsonb
);
```

### Тест 3: Запросы Cypher (аналоги AQL)

```sql
-- Получить все вершины с определенным свойством
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n:canonical_node)
    WHERE n.kind = 'concept'
    RETURN n.arango_key, n.name
$$) as (key agtype, name agtype);

-- Обход графа (как в AQL OUTBOUND)
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start:canonical_node {arango_key: 'c:backend'})-[e:project_relation*1..3]->(end)
    RETURN start.name, e, end.name
$$) as (start_name agtype, edges agtype, end_name agtype);

-- Фильтр по свойствам ребра (проекты)
SELECT * FROM cypher('common_project_graph', $$
    MATCH (a)-[e:project_relation]->(b)
    WHERE 'fepro' = ANY(e.projects)
    RETURN a.name, e.projects, b.name
$$) as (from_name agtype, projects agtype, to_name agtype);
```

---

## 🔄 Откат (если что-то пошло не так)

### Откатить к ArangoDB

```bash
# На сервере
ssh vuege-server
cd ~/fedoc

# Вернуться на main ветку
git checkout main

# Контейнер ArangoDB всё ещё работает с данными
docker ps | grep fedoc-arango

# Проверить данные
docker exec fedoc-arango arangosh \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username root \
  --server.password "your_password" \
  --server.database fedoc
```

---

## 📊 Сравнение производительности

### ArangoDB (до миграции)

```aql
// Обход графа 5 уровней
FOR v, e IN 1..5 OUTBOUND 'canonical_nodes/c:backend' GRAPH common_project_graph
  LIMIT 1000
  RETURN {v: v.name, e: e.projects}
```

### PostgreSQL + AGE (после миграции)

```sql
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start {arango_key: 'c:backend'})-[e:project_relation*1..5]->(end)
    RETURN end.name, e
    LIMIT 1000
$$) as (end_name agtype, edges agtype);
```

---

## ✅ Следующие шаги

1. Обновить Python код (api_server.py, edge_validator.py)
2. Переписать все AQL запросы на Cypher
3. Обновить конфигурацию подключения к БД
4. Провести нагрузочное тестирование
5. Обновить документацию API
6. Слить feature-ветку в main

---

**Статус:** В процессе миграции  
**Текущий этап:** Готов к тестированию инициализации

