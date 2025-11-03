-- ============================================================================
-- Скрипт удаления поля projects из всех рёбер графа через Cypher
-- Использует Python скрипт для удаления через edge_validator_age
-- ============================================================================

-- Это временный скрипт. Для удаления projects используйте Python скрипт:
-- python3 scripts/remove_projects_from_edges_python.py

-- Проверка: убедиться, что большинство рёбер мигрированы
DO $$
DECLARE
    edges_in_graph INTEGER;
    edges_in_table INTEGER;
    edges_missing INTEGER;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    -- Подсчитать рёбра с projects в графе через Cypher
    SELECT COUNT(*) INTO edges_in_graph
    FROM (
        SELECT edge_id::text
        FROM cypher('common_project_graph', $$
            MATCH ()-[e:project_relation]->()
            WHERE e.projects IS NOT NULL
            RETURN id(e) as edge_id
        $$) AS (edge_id agtype)
    ) as graph_edges;
    
    -- Подсчитать рёбра в таблице
    SELECT COUNT(DISTINCT edge_id) INTO edges_in_table
    FROM public.edge_projects;
    
    edges_missing := edges_in_graph - edges_in_table;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Статистика перед удалением projects';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Рёбер с projects в графе: %', edges_in_graph;
    RAISE NOTICE 'Рёбер в таблице edge_projects: %', edges_in_table;
    RAISE NOTICE 'Рёбер без проектов в таблице: %', edges_missing;
    RAISE NOTICE '========================================';
    
    IF edges_missing > 10 THEN
        RAISE WARNING '⚠️  Найдено % рёбер с projects в графе, которых нет в таблице. Рекомендуется миграция.', edges_missing;
    ELSE
        RAISE NOTICE '✅ Большинство рёбер мигрировано. Можно удалять projects.';
    END IF;
END $$;

RAISE NOTICE 'Для удаления projects используйте Python скрипт:';
RAISE NOTICE 'python3 scripts/remove_projects_from_edges_python.py';

