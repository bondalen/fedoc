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
-- Вспомогательная функция: get_edge_projects_array
-- Получить массив ключей проектов для ребра
-- ============================================================================

CREATE OR REPLACE FUNCTION ag_catalog.get_edge_projects_array(p_edge_id BIGINT)
RETURNS TEXT[] AS $$
BEGIN
    RETURN (
        SELECT COALESCE(array_agg(p.key ORDER BY p.key), ARRAY[]::TEXT[])
        FROM public.edge_projects ep
        JOIN public.projects p ON ep.project_id = p.id
        WHERE ep.edge_id = p_edge_id
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Функция для преобразования массива проектов в agtype
CREATE OR REPLACE FUNCTION ag_catalog.projects_array_to_agtype(p_projects TEXT[])
RETURNS agtype AS $$
BEGIN
    IF p_projects IS NULL OR array_length(p_projects, 1) IS NULL THEN
        RETURN '[]'::jsonb::text::agtype;
    END IF;
    RETURN to_jsonb(p_projects)::text::agtype;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- Функция 1: get_graph_for_viewer
-- Возвращает граф с детальной информацией для визуализации
-- Использует edge_projects для фильтрации и получения проектов
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
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    IF project_filter IS NOT NULL THEN
        RETURN QUERY
        EXECUTE FORMAT('
            SELECT 
                t.edge_id, 
                t.from_id, 
                t.to_id, 
                t.from_name, 
                t.to_name, 
                t.from_key, 
                t.to_key, 
                t.from_kind, 
                t.to_kind, 
                ag_catalog.projects_array_to_agtype(
                    ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)
                ) as projects,
                t.rel_type
            FROM cypher(''common_project_graph'', $$
                MATCH (start:canonical_node {arango_key: ''%s''})
                MATCH path = (start)-[e:project_relation*1..%s]-(target)
                WITH relationships(path) as edges_list, nodes(path) as nodes_list
                UNWIND range(0, size(edges_list)-1) as i
                WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
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
                    e.relationType as rel_type
                LIMIT 5000
            $$) AS t(edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                     from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                     rel_type agtype)
            WHERE EXISTS (
                SELECT 1 
                FROM public.edge_projects ep
                JOIN public.projects p ON ep.project_id = p.id
                WHERE ep.edge_id = (t.edge_id)::text::bigint
                AND p.key = ''%s''
            )
        ', start_key, max_depth, project_filter);
    ELSE
        RETURN QUERY
        EXECUTE FORMAT('
            SELECT 
                t.edge_id, 
                t.from_id, 
                t.to_id, 
                t.from_name, 
                t.to_name, 
                t.from_key, 
                t.to_key, 
                t.from_kind, 
                t.to_kind, 
                ag_catalog.projects_array_to_agtype(
                    ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)
                ) as projects,
                t.rel_type
            FROM cypher(''common_project_graph'', $$
                MATCH (start:canonical_node {arango_key: ''%s''})
                MATCH path = (start)-[e:project_relation*1..%s]-(target)
                WITH relationships(path) as edges_list, nodes(path) as nodes_list
                UNWIND range(0, size(edges_list)-1) as i
                WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
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
                    e.relationType as rel_type
                LIMIT 5000
            $$) AS t(edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                     from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                     rel_type agtype)
        ', start_key, max_depth);
    END IF;
END;
$func$;

\echo '✓ Функция get_graph_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 2: get_all_graph_for_viewer
-- Возвращает все связи графа для визуализации
-- Использует edge_projects для фильтрации и получения проектов
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
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    IF project_filter IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            t.edge_id, 
            t.from_id, 
            t.to_id, 
            t.from_name, 
            t.to_name, 
            t.from_key, 
            t.to_key, 
            t.from_kind, 
            t.to_kind, 
            ag_catalog.projects_array_to_agtype(
                ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)
            ) as projects,
            t.rel_type
        FROM cypher('common_project_graph', $$
            MATCH (n:canonical_node)-[e:project_relation]->(m:canonical_node)
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
                e.relationType as rel_type
            LIMIT 5000
        $$) AS t(edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                 from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                 rel_type agtype)
        WHERE EXISTS (
            SELECT 1 
            FROM public.edge_projects ep
            JOIN public.projects p ON ep.project_id = p.id
            WHERE ep.edge_id = (t.edge_id)::text::bigint
            AND p.key = project_filter
        );
    ELSE
        RETURN QUERY
        SELECT 
            t.edge_id, 
            t.from_id, 
            t.to_id, 
            t.from_name, 
            t.to_name, 
            t.from_key, 
            t.to_key, 
            t.from_kind, 
            t.to_kind, 
            ag_catalog.projects_array_to_agtype(
                ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)
            ) as projects,
            t.rel_type
        FROM cypher('common_project_graph', $$
            MATCH (n:canonical_node)-[e:project_relation]->(m:canonical_node)
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
                e.relationType as rel_type
            LIMIT 5000
        $$) AS t(edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype,
                 from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, 
                 rel_type agtype);
    END IF;
END;
$func$;

\echo '✓ Функция get_all_graph_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 3: expand_node_for_viewer
-- Расширяет узел на определенную глубину
-- Использует edge_projects для фильтрации
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
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    IF project_filter IS NOT NULL THEN
        RETURN QUERY
        EXECUTE FORMAT('
            SELECT 
                t.node_id,
                t.node_key,
                t.node_name,
                t.node_kind,
                t.edge_id,
                t.from_id,
                t.to_id,
                COALESCE(
                    (SELECT to_jsonb(ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)))::agtype,
                    ''[]''::jsonb::agtype
                ) as edge_projects,
                t.direction
            FROM cypher(''common_project_graph'', $$
                MATCH (start:canonical_node {arango_key: ''%s''})
                MATCH path = (start)-[*1..%s]-(target:canonical_node)
                WITH relationships(path) as edges_list, target
                UNWIND edges_list as e
                RETURN DISTINCT
                    id(target)::text as node_id,
                    target.arango_key as node_key,
                    target.name as node_name,
                    target.kind as node_kind,
                    id(e)::text as edge_id,
                    id(startNode(e))::text as from_id,
                    id(endNode(e))::text as to_id,
                    ''both'' as direction
            $$) AS (node_id agtype, node_key agtype, node_name agtype, node_kind agtype,
                    edge_id agtype, from_id agtype, to_id agtype, direction agtype) t
            WHERE EXISTS (
                SELECT 1 
                FROM public.edge_projects ep
                JOIN public.projects p ON ep.project_id = p.id
                WHERE ep.edge_id = (t.edge_id)::text::bigint
                AND p.key = ''%s''
            )
        ', node_key_param, max_depth, project_filter);
    ELSE
        RETURN QUERY
        EXECUTE FORMAT('
            SELECT 
                t.node_id,
                t.node_key,
                t.node_name,
                t.node_kind,
                t.edge_id,
                t.from_id,
                t.to_id,
                COALESCE(
                    (SELECT to_jsonb(ag_catalog.get_edge_projects_array((t.edge_id)::text::bigint)))::agtype,
                    ''[]''::jsonb::agtype
                ) as edge_projects,
                t.direction
            FROM cypher(''common_project_graph'', $$
                MATCH (start:canonical_node {arango_key: ''%s''})
                MATCH path = (start)-[*1..%s]-(target:canonical_node)
                WITH relationships(path) as edges_list, target
                UNWIND edges_list as e
                RETURN DISTINCT
                    id(target)::text as node_id,
                    target.arango_key as node_key,
                    target.name as node_name,
                    target.kind as node_kind,
                    id(e)::text as edge_id,
                    id(startNode(e))::text as from_id,
                    id(endNode(e))::text as to_id,
                    ''both'' as direction
            $$) AS (node_id agtype, node_key agtype, node_name agtype, node_kind agtype,
                    edge_id agtype, from_id agtype, to_id agtype, direction agtype) t
        ', node_key_param, max_depth);
    END IF;
END;
$func$;

\echo '✓ Функция expand_node_for_viewer() создана'
\echo ''

-- ============================================================================
-- Функция 4: get_all_nodes_for_viewer
-- Возвращает список всех узлов
-- Использует edge_projects для фильтрации
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
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    IF project_filter IS NOT NULL THEN
        RETURN QUERY
        SELECT DISTINCT 
            t.node_id, 
            t.node_key, 
            t.node_name
        FROM cypher('common_project_graph', $$
            MATCH (n:canonical_node)<-[e:project_relation]-()
            RETURN DISTINCT 
                id(n)::text as node_id, 
                n.arango_key as node_key, 
                n.name as node_name,
                id(e)::text as edge_id
        $$) AS t(node_id agtype, node_key agtype, node_name agtype, edge_id agtype)
        WHERE EXISTS (
            SELECT 1 
            FROM public.edge_projects ep
            JOIN public.projects p ON ep.project_id = p.id
            WHERE ep.edge_id = (t.edge_id)::text::bigint
            AND p.key = project_filter
        );
    ELSE
        RETURN QUERY
        SELECT *
        FROM cypher('common_project_graph', $$
            MATCH (n:canonical_node)
            RETURN 
                id(n)::text as node_id, 
                n.arango_key as node_key, 
                n.name as node_name
        $$) AS (node_id agtype, node_key agtype, node_name agtype);
    END IF;
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

