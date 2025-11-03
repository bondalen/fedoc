-- ============================================================================
-- Скрипт удаления поля projects из всех рёбер графа
-- 
-- ВАЖНО: Выполнять ТОЛЬКО после успешной миграции всех данных в edge_projects
-- и проверки целостности через verify_edge_projects_integrity.py
-- ============================================================================

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
    FROM cypher('common_project_graph', $$
        MATCH ()-[e:project_relation]->()
        WHERE e.projects IS NOT NULL
        RETURN id(e) as edge_id
    $$) AS (edge_id agtype);
    
    -- Подсчитать рёбра в таблице
    SELECT COUNT(DISTINCT edge_id) INTO edges_in_table
    FROM public.edge_projects;
    
    edges_missing := edges_in_graph - edges_in_table;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Проверка перед удалением projects';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Рёбер с projects в графе: %', edges_in_graph;
    RAISE NOTICE 'Рёбер в таблице edge_projects: %', edges_in_table;
    RAISE NOTICE 'Рёбер без проектов в таблице: %', edges_missing;
    RAISE NOTICE '========================================';
    
    IF edges_missing > 10 THEN
        RAISE EXCEPTION 'Найдено % рёбер с projects в графе, которых нет в таблице. Сначала выполните миграцию!', edges_missing;
    ELSIF edges_missing > 0 THEN
        RAISE WARNING 'Обнаружено % рёбер без проектов в таблице. Продолжаем удаление...', edges_missing;
    END IF;
    
    RAISE NOTICE '✅ Проверка пройдена. Удаляем projects из рёбер...';
END $$;

-- Удалить поле projects из всех рёбер через Cypher
DO $$
DECLARE
    edge_record RECORD;
    updated_count INTEGER := 0;
    edge_id_val BIGINT;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    -- Пройти по всем рёбрам с полем projects через Cypher
    FOR edge_record IN 
        SELECT edge_id::text as edge_id_str
        FROM cypher('common_project_graph', $$
            MATCH ()-[e:project_relation]->()
            WHERE e.projects IS NOT NULL
            RETURN id(e) as edge_id
        $$) AS (edge_id agtype)
    LOOP
        BEGIN
            edge_id_val := (edge_record.edge_id_str)::bigint;
            
            -- Удалить поле projects через Cypher
            PERFORM * FROM cypher('common_project_graph', $$
                MATCH ()-[e]->()
                WHERE id(e) = $edge_id
                SET e = apoc.map.removeKeys(e, ['projects'])
                RETURN id(e)
            $$, json_build_object('edge_id', edge_id_val)::jsonb);
            
            -- Альтернативный способ: через REMOVE
            PERFORM * FROM cypher('common_project_graph', FORMAT($$
                MATCH ()-[e]->()
                WHERE id(e) = %s
                REMOVE e.projects
                RETURN id(e)
            $$, edge_id_val)) AS (edge_id agtype);
            
            updated_count := updated_count + 1;
            
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при удалении projects из ребра %: %', edge_id_val, SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE '✅ Удалено поле projects из % рёбер', updated_count;
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Миграция завершена!';
    RAISE NOTICE 'Все проекты теперь хранятся в таблице edge_projects';
    RAISE NOTICE '========================================';
END $$;

-- Финальная проверка: убедиться, что projects удалены
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog, public;
    
    SELECT COUNT(*) INTO remaining_count
    FROM cypher('common_project_graph', $$
        MATCH ()-[e:project_relation]->()
        WHERE e.projects IS NOT NULL
        RETURN id(e) as edge_id
    $$) AS (edge_id agtype);
    
    IF remaining_count > 0 THEN
        RAISE WARNING '⚠️  ВНИМАНИЕ: Осталось % рёбер с полем projects!', remaining_count;
    ELSE
        RAISE NOTICE '✅ Все поля projects успешно удалены из рёбер';
    END IF;
END $$;

