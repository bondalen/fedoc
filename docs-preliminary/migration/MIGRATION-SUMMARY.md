# Миграция fedoc с ArangoDB на PostgreSQL + Apache AGE

**Дата начала:** 18 октября 2025  
**Версии:**
- PostgreSQL: 16.10
- Apache AGE: 1.6.0
- Сервер: 176.108.244.252 (контейнер fedoc-postgres)

---

## 📊 Проверка версий (completed ✅)

### PostgreSQL 16.10
```
PostgreSQL 16.10 on x86_64-pc-linux-musl, compiled by gcc (Alpine 14.2.0) 14.2.0, 64-bit
```

### Apache AGE 1.6.0
```
 name | default_version | installed_version |        comment         
------+-----------------+-------------------+------------------------
 age  | 1.6.0           | 1.6.0             | AGE database extension
```

**Вывод:** Версии актуальные и совместимые! ✅

---

## 🎯 Текущая структура ArangoDB

### Коллекции (Collections)

**Document Collections:**
1. `canonical_nodes` - канонические узлы (концепции и технологии)
2. `projects` - проекты (fedoc, fepro, femsq)

**Edge Collections:**
1. `project_relations` - связи между узлами графа

**Named Graphs:**
1. `common_project_graph` - общий граф проектов

### Структура данных

**canonical_nodes:**
```json
{
  "_key": "c:backend",
  "_id": "canonical_nodes/c:backend",
  "name": "Backend",
  "kind": "concept"
}
```

**project_relations:**
```json
{
  "_from": "canonical_nodes/c:project",
  "_to": "canonical_nodes/c:dev-objects",
  "relationType": "contains",
  "projects": ["fepro", "femsq", "fedoc"],
  "weight": 3
}
```

---

## 🔄 Текущие запросы AQL

### 1. Получение узлов (с фильтром по проекту)
```aql
LET verts = (
  FOR e IN project_relations 
  FILTER @project IN e.projects 
  RETURN [e._from, e._to]
)
LET flattened = FLATTEN(verts)
LET unique_verts = UNIQUE(flattened)
FOR vid IN unique_verts
  LET d = DOCUMENT(vid)
  FILTER d != null
  RETURN { _id: d._id, _key: d._key, name: d.name }
```

### 2. Получение графа (обход)
```aql
FOR v, e IN 1..@depth OUTBOUND @start_node GRAPH @graph
    LIMIT @max_nodes
    RETURN {
        edge_id: e._id,
        from: e._from,
        to: e._to,
        from_name: DOCUMENT(e._from).name,
        to_name: DOCUMENT(e._to).name,
        projects: e.projects,
        type: e.relationType
    }
```

### 3. Расширение узла (expand_node)
```aql
FOR v, e IN 1..1 OUTBOUND @node GRAPH @graph
    RETURN {
        node: v,
        edge: e
    }
```

### 4. Получение подграфа (subgraph)
```aql
FOR v, e, p IN 1..@depth OUTBOUND @node GRAPH @graph
    RETURN {
        node_id: v._id,
        edge_id: e._id,
        edge_projects: e.projects
    }
```

### 5. Валидация уникальности ребра
```aql
FOR e IN project_relations
    FILTER (e._from == @from AND e._to == @to) 
        OR (e._from == @to AND e._to == @from)
    FILTER e._id != @exclude_id
    LIMIT 1 
    RETURN {_id: e._id, _from: e._from, _to: e._to}
```

---

## 🎯 Обоснование миграции

Согласно `docs-preliminary/analysis/FINAL-RECOMMENDATION.md`:

✅ **PostgreSQL позволяет** создавать функции (в отличие от ArangoDB CE)  
✅ **Функции могут** централизовать логику в БД  
✅ **Это упрощает** приложение (1 вызов вместо 2)  
✅ **Дает атомарность** (проверка + создание в одной транзакции)  
✅ **Подтверждено:** Хранимые процедуры могут вызывать cypher()

---

## 📋 План миграции

### Этап 1: Схема базы данных ⏳
- [ ] Создать базу данных `fedoc`
- [ ] Установить расширение Apache AGE
- [ ] Создать граф `common_project_graph`
- [ ] Спроектировать структуру вершин и рёбер

### Этап 2: Функции валидации ⏳
- [ ] Создать функцию проверки уникальности рёбер
- [ ] Создать функцию безопасного добавления ребра
- [ ] Создать функцию обновления ребра
- [ ] Создать функцию удаления ребра

### Этап 3: Миграция данных ⏳
- [ ] Экспортировать данные из ArangoDB
- [ ] Скрипт миграции узлов
- [ ] Скрипт миграции рёбер
- [ ] Валидация данных

### Этап 4: Переписывание запросов ⏳
- [ ] AQL → Cypher: получение узлов
- [ ] AQL → Cypher: обход графа
- [ ] AQL → Cypher: расширение узла
- [ ] AQL → Cypher: получение подграфа

### Этап 5: Обновление кода ⏳
- [ ] Заменить python-arango на psycopg2 + AGE
- [ ] Обновить api_server.py
- [ ] Обновить edge_validator.py
- [ ] Обновить конфигурацию

### Этап 6: Тестирование ⏳
- [ ] Тест подключения к PostgreSQL
- [ ] Тест создания/обновления/удаления рёбер
- [ ] Тест запросов графа
- [ ] Интеграционные тесты

---

**Статус:** В процессе  
**Текущий этап:** Проектирование схемы

