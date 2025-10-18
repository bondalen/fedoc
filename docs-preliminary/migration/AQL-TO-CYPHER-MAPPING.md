# Маппинг запросов AQL → Cypher для fedoc

**Цель:** Переписать все запросы из `api_server.py` с AQL на Cypher для Apache AGE

---

## 1. Получение узлов (с фильтром по проекту)

### AQL (текущий)

```python
query = """
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
"""
bind_vars = {'project': project}
```

### Cypher (новый)

```python
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (a)-[e:project_relation]->(b)
    WHERE $project = ANY(e.projects)
    WITH DISTINCT a as node
    RETURN id(node) as id, node.arango_key as key, node.name as name
    UNION
    MATCH (a)-[e:project_relation]->(b)
    WHERE $project = ANY(e.projects)
    WITH DISTINCT b as node
    RETURN id(node) as id, node.arango_key as key, node.name as name
$$, $params$
    {"project": "%s"}
$params$) as (id agtype, key agtype, name agtype)
""" % project

# Или через параметризованный запрос
```

**Примечание:** В AGE параметры передаются через `$params$` блок в JSON формате.

---

## 2. Получение узлов (без фильтра)

### AQL

```python
query = "FOR d IN canonical_nodes RETURN {_id: d._id, _key: d._key, name: d.name}"
```

### Cypher

```python
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n:canonical_node)
    RETURN id(n) as id, n.arango_key as key, n.name as name
$$) as (id agtype, key agtype, name agtype)
"""
```

---

## 3. Построение графа (OUTBOUND обход)

### AQL

```python
query = """
FOR v, e IN 1..@depth OUTBOUND @start_node GRAPH @graph
    LIMIT @max_nodes
    RETURN {
        edge_id: e._id,
        from: e._from,
        to: e._to,
        from_name: DOCUMENT(e._from).name,
        to_name: DOCUMENT(e._to).name,
        from_key: DOCUMENT(e._from)._key,
        to_key: DOCUMENT(e._to)._key,
        from_kind: DOCUMENT(e._from).kind,
        to_kind: DOCUMENT(e._to).kind,
        projects: e.projects,
        type: e.relationType
    }
"""
bind_vars = {
    'start_node': start,
    'depth': depth,
    'graph': 'common_project_graph',
    'max_nodes': 5000
}
```

### Cypher

```python
# Получить ID стартовой вершины по arango_key
start_key = start.split('/')[-1]  # Извлечь key из "canonical_nodes/c:backend"

query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start:canonical_node {arango_key: $start_key})
    MATCH path = (start)-[e:project_relation*1..%d]->(end)
    WITH relationships(path) as edges, nodes(path) as nodes_list
    UNWIND range(0, size(edges)-1) as i
    WITH edges[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
    RETURN 
        id(e) as edge_id,
        id(from_node) as from_id,
        id(to_node) as to_id,
        from_node.name as from_name,
        to_node.name as to_name,
        from_node.arango_key as from_key,
        to_node.arango_key as to_key,
        from_node.kind as from_kind,
        to_node.kind as to_kind,
        e.projects as projects,
        e.relationType as type
    LIMIT %d
$$, $params$
    {"start_key": "%s"}
$params$) as (
    edge_id agtype,
    from_id agtype,
    to_id agtype,
    from_name agtype,
    to_name agtype,
    from_key agtype,
    to_key agtype,
    from_kind agtype,
    to_kind agtype,
    projects agtype,
    type agtype
)
""" % (depth, max_nodes, start_key)
```

---

## 4. Расширение узла (expand_node)

### AQL (OUTBOUND)

```python
query = """
FOR v, e IN 1..1 OUTBOUND @node GRAPH @graph
    RETURN {
        node: v,
        edge: e
    }
"""
```

### Cypher (OUTBOUND)

```python
# node_id - это ID вершины в AGE (bigint)
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start)-[e:project_relation]->(end)
    WHERE id(start) = %d
    RETURN end as node, e as edge
$$) as (node agtype, edge agtype)
""" % node_id
```

### AQL (INBOUND)

```python
query = """
FOR v, e IN 1..1 INBOUND @node GRAPH @graph
    RETURN {
        node: v,
        edge: e
    }
"""
```

### Cypher (INBOUND)

```python
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start)<-[e:project_relation]-(end)
    WHERE id(start) = %d
    RETURN end as node, e as edge
$$) as (node agtype, edge agtype)
""" % node_id
```

---

## 5. Получение подграфа (subgraph)

### AQL (OUTBOUND)

```python
query = """
FOR v, e, p IN 1..@depth OUTBOUND @node GRAPH @graph
    RETURN {
        node_id: v._id,
        edge_id: e._id,
        edge_projects: e.projects
    }
"""
```

### Cypher (OUTBOUND)

```python
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (start)-[e:project_relation*1..%d]->(end)
    WHERE id(start) = %d
    WITH e as edges_list, end
    UNWIND edges_list as edge
    RETURN DISTINCT 
        id(end) as node_id,
        id(edge) as edge_id,
        edge.projects as edge_projects
$$) as (node_id agtype, edge_id agtype, edge_projects agtype)
""" % (max_depth, node_id)
```

---

## 6. Получение детального объекта

### AQL

```python
query = "RETURN DOCUMENT(@id)"
bind_vars = {'id': doc_id}
```

### Cypher

```python
# Если doc_id - это ID вершины в AGE
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n)
    WHERE id(n) = %d
    RETURN n
$$) as (node agtype)
""" % node_id

# Если doc_id - это arango_id (например "canonical_nodes/c:backend")
arango_key = doc_id.split('/')[-1]
query = """
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n:canonical_node {arango_key: $key})
    RETURN n
$$, $params$
    {"key": "%s"}
$params$) as (node agtype)
""" % arango_key
```

---

## 7. Валидация уникальности ребра

### AQL

```python
query = """
FOR e IN project_relations
    FILTER (e._from == @from AND e._to == @to) 
        OR (e._from == @to AND e._to == @from)
    FILTER e._id != @exclude_id
    LIMIT 1 
    RETURN {_id: e._id, _from: e._from, _to: e._to}
"""
```

### Cypher (используем функцию PostgreSQL!)

```python
# Используем функцию check_edge_uniqueness() вместо прямого запроса
query = """
SELECT * FROM check_edge_uniqueness(
    'common_project_graph',
    %d::bigint,
    %d::bigint,
    %s
)
""" % (from_vertex_id, to_vertex_id, exclude_edge_id or 'NULL')
```

---

## Важные отличия AGE от ArangoDB

### 1. ID вершин и рёбер

- **ArangoDB:** `_id` строковый, например `"canonical_nodes/12345"`
- **AGE:** `id()` возвращает `bigint`
- **Решение:** Сохранять `arango_key` как свойство для обратной совместимости

### 2. Свойства

- **ArangoDB:** Прямой доступ `e._from`, `e._to`
- **AGE:** Свойства через `.` но `_from`/`_to` не существуют
- **Решение:** Использовать `id(start)`, `id(end)` в MATCH

### 3. Параметры запросов

- **ArangoDB:** Bind variables `@param`
- **AGE:** JSON блок `$params$ {...} $params$` и ссылка через `$param`

### 4. Типы данных

- **ArangoDB:** Автоматическое преобразование типов
- **AGE:** `agtype` требует явного приведения через `::text`, `::bigint`

### 5. Массивы

- **ArangoDB:** `'value' IN array`
- **Cypher:** `'value' = ANY(array)` или `'value' IN array`

---

## Рекомендации по переписыванию

1. **Создать helper-функции** для частых операций:
   - `get_vertex_id_by_arango_key(key)` → bigint
   - `get_vertex_by_id(id)` → vertex object
   - `convert_agtype_to_dict(agtype)` → Python dict

2. **Использовать функции PostgreSQL** вместо прямых запросов:
   - ✅ `create_edge_safe()` вместо прямого CREATE
   - ✅ `check_edge_uniqueness()` вместо запроса дубликатов

3. **Кэшировать маппинг ID:**
   - Сохранить `arango_key → age_id` в Redis или памяти
   - Ускорит преобразование ID

4. **Тестировать каждый запрос:**
   - Сравнить результаты AQL и Cypher на реальных данных
   - Проверить производительность

---

**Следующий шаг:** Обновить `api_server.py` с новыми Cypher запросами

