-- Ручная миграция данных в PostgreSQL AGE
LOAD 'age';
SET search_path = ag_catalog, public;

-- Создать несколько ключевых узлов
SELECT * FROM cypher('common_project_graph', $$
    CREATE (n:canonical_node {name: 'Проект', arango_key: 'c:project'})
    RETURN id(n)
$$) as (id agtype);

SELECT * FROM cypher('common_project_graph', $$
    CREATE (n:canonical_node {name: 'Объекты разработки', arango_key: 'c:dev-objects'})
    RETURN id(n)
$$) as (id agtype);

SELECT * FROM cypher('common_project_graph', $$
    CREATE (n:canonical_node {name: 'Слой', arango_key: 'c:layer'})
    RETURN id(n)
$$) as (id agtype);

SELECT * FROM cypher('common_project_graph', $$
    CREATE (n:canonical_node {name: 'Бэкенд', arango_key: 'c:backend'})
    RETURN id(n)
$$) as (id agtype);

SELECT * FROM cypher('common_project_graph', $$
    CREATE (n:canonical_node {name: 'БД проекта', arango_key: 'c:project-database'})
    RETURN id(n)
$$) as (id agtype);

-- Проверить результат
SELECT * FROM cypher('common_project_graph', $$
    MATCH (n) RETURN count(n)
$$) as (cnt agtype);

SELECT * FROM cypher('common_project_graph', $$
    MATCH (n) RETURN n.name, n.arango_key
$$) as (name agtype, key agtype);
