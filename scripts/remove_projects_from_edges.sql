-- ============================================================================
-- Скрипт удаления поля projects из всех рёбер графа
-- 
-- ВАЖНО: Выполнять ТОЛЬКО после успешной миграции всех данных в edge_projects
-- и проверки целостности через verify_edge_projects_integrity.py
-- ============================================================================

-- Проверка: убедиться, что все рёбра с projects мигрированы
DO $$
DECLARE
    edges_in_graph INTEGER;
    edges_in_table INTEGER;
    edges_missing INTEGER;
BEGIN
    -- Подсчитать рёбра с projects в графе
    LOAD 'age';
    SET search_path = ag_catalog, public;
    
    SELECT COUNT(*) INTO edges_in_graph
    FROM ag_edge e
    WHERE e.label = 'project_relation'
    AND agtype_to_json(e.properties)::jsonb ? 'projects';
    
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
    
    IF edges_missing > 0 THEN
        RAISE EXCEPTION 'Найдено % рёбер с projects в графе, которых нет в таблице. Сначала выполните миграцию!', edges_missing;
    END IF;
    
    RAISE NOTICE '✅ Проверка пройдена. Удаляем projects из рёбер...';
END $$;

-- Удалить поле projects из всех рёбер
DO $$
DECLARE
    edge_record RECORD;
    updated_count INTEGER := 0;
    properties_json JSONB;
    new_properties JSONB;
BEGIN
    LOAD 'age';
    SET search_path = ag_catalog, public;
    
    -- Пройти по всем рёбрам с полем projects
    FOR edge_record IN 
        SELECT 
            e.id,
            agtype_to_json(e.properties)::jsonb as properties
        FROM ag_edge e
        WHERE e.label = 'project_relation'
        AND agtype_to_json(e.properties)::jsonb ? 'projects'
    LOOP
        -- Удалить поле projects из properties
        properties_json := edge_record.properties;
        new_properties := properties_json - 'projects';
        
        -- Обновить ребро (нужно использовать UPDATE через SQL)
        -- Примечание: Apache AGE не поддерживает прямой UPDATE через SQL,
        -- нужно использовать Cypher, но здесь мы используем прямой доступ к ag_edge
        
        -- Преобразовать обратно в agtype
        UPDATE ag_edge
        SET properties = json_to_agtype(new_properties::text)
        WHERE id = edge_record.id;
        
        updated_count := updated_count + 1;
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
    SET search_path = ag_catalog, public;
    
    SELECT COUNT(*) INTO remaining_count
    FROM ag_edge e
    WHERE e.label = 'project_relation'
    AND agtype_to_json(e.properties)::jsonb ? 'projects';
    
    IF remaining_count > 0 THEN
        RAISE WARNING '⚠️  ВНИМАНИЕ: Осталось % рёбер с полем projects!', remaining_count;
    ELSE
        RAISE NOTICE '✅ Все поля projects успешно удалены из рёбер';
    END IF;
END $$;

