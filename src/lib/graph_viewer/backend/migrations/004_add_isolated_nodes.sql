-- Миграция 004: Добавление изолированных узлов в get_all_graph_for_viewer
-- Дата: 2025-10-27
-- Описание: Модификация функции для отображения изолированных узлов

CREATE OR REPLACE FUNCTION ag_catalog.get_all_graph_for_viewer(project_filter TEXT DEFAULT NULL)
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
) AS $$
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
    
    -- Получаем все рёбра
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
                 projects agtype, rel_type agtype)
    ', where_clause);
    
    RETURN QUERY EXECUTE sql;
    
    -- Добавляем изолированные узлы
    RETURN QUERY
    SELECT 
        NULL::agtype as edge_id,
        (n->>'id')::agtype as from_id,
        NULL::agtype as to_id,
        (n->>'name')::agtype as from_name,
        NULL::agtype as to_name,
        (n->>'arango_key')::agtype as from_key,
        NULL::agtype as to_key,
        (n->>'kind')::agtype as from_kind,
        NULL::agtype as to_kind,
        NULL::agtype as projects,
        '"isolated"'::agtype as rel_type
    FROM cypher('common_project_graph', $$
        MATCH (n:canonical_node)
        WHERE NOT (n)-[:project_relation]-()
        RETURN n
    $$) AS (n agtype);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ag_catalog.get_all_graph_for_viewer(TEXT) IS 'Получить все рёбра и изолированные узлы для визуализации графа';






