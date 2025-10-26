-- ============================================================================
-- Функции для Graph Viewer в PostgreSQL + Apache AGE
-- 
-- Специализированные функции с правильным форматом данных для frontend
-- Используют FORMAT() для динамической генерации запросов
-- ============================================================================

\echo '================================================'
\echo 'Создание функций для Graph Viewer'
\echo '================================================'

\c fedoc

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- ============================================================================
-- Функция 1: get_graph_for_viewer
-- Возвращает граф с детальной информацией для визуализации
-- ============================================================================

\echo 'Создание функции get_graph_for_viewer()...'

CREATE OR REPLACE FUNCTION ag_catalog.get_graph_for_viewer(
    start_key TEXT,
    max_depth INTEGER,
    project_filter TEXT DEFAULT NULL
)
RETURNS TABLE(
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
    rel_type agtype
)
LANGUAGE plpgsql
AS $func$
DECLARE 
    sql VARCHAR;
    where_clause TEXT;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog;
    
    -- Формируем WHERE для фильтрации по проекту
    IF project_filter IS NOT NULL THEN
        where_clause := FORMAT('WHERE ''%s'' IN e.projects', project_filter);
    ELSE
        where_clause := '';
    END IF;
    
    sql := FORMAT('
        SELECT *
        FROM cypher(''common_project_graph'', $$
            MATCH (start:canonical_node {arango_key: ''%s''})
            MATCH path = (start)-[e:project_relation*1..%s]-(target)
            WITH relationships(path) as edges_list, nodes(path) as nodes_list
            UNWIND range(0, size(edges_list)-1) as i
            WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
            %s
            RETURN 
                id(e)::text as edge_id,
                id(from_node)::text as from_id,
                id(to_node)::text as to_id,
                from_node.name as from_name,
                to_node.name as to_name,
                from_node.arango_key as from_key,
                to_node.arango_key as to_key,
                from_node.kind as from_kind,
                to_node.kind as to_kind,
                e.projects::text as projects,
                e.relationType as rel_type
            LIMIT 5000
        $$) AS (edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                projects agtype, rel_type agtype);
    ', start_key, max_depth, where_clause);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;

\echo '✓ Функция get_graph_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 2: get_all_graph_for_viewer
-- Возвращает все связи графа для визуализации
-- ============================================================================

\echo 'Создание функции get_all_graph_for_viewer()...'

CREATE OR REPLACE FUNCTION ag_catalog.get_all_graph_for_viewer(
    project_filter TEXT DEFAULT NULL
)
RETURNS TABLE(
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
    rel_type agtype
)
LANGUAGE plpgsql
AS $func$
DECLARE 
    sql VARCHAR;
    where_clause TEXT;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog;
    
    -- Формируем WHERE для фильтрации по проекту
    IF project_filter IS NOT NULL THEN
        where_clause := FORMAT('WHERE ''%s'' IN e.projects', project_filter);
    ELSE
        where_clause := '';
    END IF;
    
    sql := FORMAT('
        SELECT *
        FROM cypher(''common_project_graph'', $$
            MATCH (n:canonical_node)-[e:project_relation]->(m:canonical_node)
            %s
            RETURN 
                id(e)::text as edge_id,
                id(n)::text as from_id,
                id(m)::text as to_id,
                n.name as from_name,
                m.name as to_name,
                n.arango_key as from_key,
                m.arango_key as to_key,
                n.kind as from_kind,
                m.kind as to_kind,
                e.projects::text as projects,
                e.relationType as rel_type
            LIMIT 5000
        $$) AS (edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                projects agtype, rel_type agtype);
    ', where_clause);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;

\echo '✓ Функция get_all_graph_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 3: expand_node_for_viewer
-- Расширяет узел на определенную глубину
-- ============================================================================

\echo 'Создание функции expand_node_for_viewer()...'

CREATE OR REPLACE FUNCTION ag_catalog.expand_node_for_viewer(
    node_key_param TEXT,
    max_depth INTEGER DEFAULT 1,
    project_filter TEXT DEFAULT NULL
)
RETURNS TABLE(
    node_id agtype,
    node_key agtype,
    node_name agtype,
    node_kind agtype,
    edge_id agtype,
    from_id agtype,
    to_id agtype,
    edge_projects agtype,
    direction agtype
)
LANGUAGE plpgsql
AS $func$
DECLARE 
    sql VARCHAR;
    where_clause TEXT;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog;
    
    IF project_filter IS NOT NULL THEN
        where_clause := FORMAT('WHERE ''%s'' IN e.projects', project_filter);
    ELSE
        where_clause := '';
    END IF;
    
    sql := FORMAT('
        SELECT *
        FROM cypher(''common_project_graph'', $$
            MATCH (start:canonical_node {arango_key: ''%s''})
            MATCH path = (start)-[*1..%s]-(target:canonical_node)
            WITH relationships(path) as edges_list, target
            UNWIND edges_list as e
            %s
            RETURN DISTINCT
                id(target)::text as node_id,
                target.arango_key as node_key,
                target.name as node_name,
                target.kind as node_kind,
                id(e)::text as edge_id,
                id(startNode(e))::text as from_id,
                id(endNode(e))::text as to_id,
                e.projects::text as edge_projects,
                ''both'' as direction
        $$) AS (node_id agtype, node_key agtype, node_name agtype, node_kind agtype,
                edge_id agtype, from_id agtype, to_id agtype, edge_projects agtype, direction agtype);
    ', node_key_param, max_depth, where_clause);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;

\echo '✓ Функция expand_node_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 4: get_all_nodes_for_viewer
-- Возвращает список всех узлов
-- ============================================================================

\echo 'Создание функции get_all_nodes_for_viewer()...'

CREATE OR REPLACE FUNCTION ag_catalog.get_all_nodes_for_viewer(
    project_filter TEXT DEFAULT NULL
)
RETURNS TABLE(
    node_id agtype,
    node_key agtype,
    node_name agtype
)
LANGUAGE plpgsql
AS $func$
DECLARE 
    sql VARCHAR;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog;
    
    IF project_filter IS NOT NULL THEN
        sql := FORMAT('
            SELECT *
            FROM cypher(''common_project_graph'', $$
                MATCH (n:canonical_node)<-[e:project_relation]-(m)
                WHERE ''%s'' IN e.projects
                RETURN DISTINCT 
                    id(n)::text as node_id, 
                    n.arango_key as node_key, 
                    n.name as node_name
            $$) AS (node_id agtype, node_key agtype, node_name agtype);
        ', project_filter);
    ELSE
        sql := '
            SELECT *
            FROM cypher(''common_project_graph'', $$
                MATCH (n:canonical_node)
                RETURN 
                    id(n)::text as node_id, 
                    n.arango_key as node_key, 
                    n.name as node_name
            $$) AS (node_id agtype, node_key agtype, node_name agtype);
        ';
    END IF;
    
    RETURN QUERY EXECUTE sql;
END;
$func$;

\echo '✓ Функция get_all_nodes_for_viewer() создана'
\echo ''

\echo '================================================'
\echo 'Функции для Graph Viewer созданы успешно!'
\echo '================================================'
\echo ''
\echo 'Созданы функции:'
\echo '  1. get_graph_for_viewer(start_key, max_depth, project_filter)'
\echo '  2. get_all_graph_for_viewer(project_filter)'
\echo '  3. expand_node_for_viewer(node_key, max_depth, project_filter)'
\echo '  4. get_all_nodes_for_viewer(project_filter)'
\echo ''
\echo 'Готово к использованию в API сервере!'
\echo ''

