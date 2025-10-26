-- Миграция 003: Упрощённая миграция существующих данных проектов в рёбрах
-- Дата: 2025-01-20
-- Описание: Перенос данных из поля properties.projects в нормализованную структуру

-- Основная миграция данных
DO $$
DECLARE
    edge_record RECORD;
    project_key TEXT;
    projects_list TEXT[];
    project_count INTEGER := 0;
    total_edges INTEGER := 0;
    properties_json JSONB;
BEGIN
    RAISE NOTICE 'Начинаем миграцию данных проектов в рёбрах...';
    
    -- Подсчитать общее количество рёбер для обработки
    SELECT COUNT(*) INTO total_edges
    FROM common_project_graph.project_relation;
    
    RAISE NOTICE 'Найдено % рёбер для обработки', total_edges;
    
    -- Пройти по всем рёбрам
    FOR edge_record IN 
        SELECT id, properties 
        FROM common_project_graph.project_relation
    LOOP
        -- Преобразовать agtype в JSON
        properties_json := ag_catalog.agtype_to_json(edge_record.properties);
        
        -- Проверить наличие поля projects
        IF properties_json ? 'projects' AND jsonb_typeof(properties_json->'projects') = 'array' THEN
            -- Извлечь список проектов
            projects_list := ARRAY(
                SELECT jsonb_array_elements_text(properties_json->'projects')
            );
            
            -- Добавить каждый проект в нормализованную структуру
            FOR project_key IN SELECT unnest(projects_list)
            LOOP
                BEGIN
                    -- Добавить связь в нормализованную таблицу
                    -- Преобразовать ag_catalog.graphid в BIGINT
                    INSERT INTO public.edge_projects (edge_id, project_id, role, weight, created_by, metadata)
                    SELECT 
                        edge_record.id::BIGINT,
                        p.id,
                        'participant',
                        1.0,
                        'migration',
                        jsonb_build_object(
                            'migrated_from', 'properties.projects',
                            'migration_date', NOW()
                        )
                    FROM public.projects p
                    WHERE p.key = project_key
                    ON CONFLICT (edge_id, project_id) DO NOTHING;
                    
                    project_count := project_count + 1;
                    
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'Ошибка при добавлении проекта % к ребру %: %', 
                        project_key, edge_record.id, SQLERRM;
                END;
            END LOOP;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Миграция завершена. Добавлено % связей проект-ребро', project_count;
END $$;

-- Проверка результатов миграции
DO $$
DECLARE
    total_relations INTEGER;
    edges_with_projects INTEGER;
    projects_in_relations INTEGER;
BEGIN
    -- Подсчитать общее количество связей
    SELECT COUNT(*) INTO total_relations FROM public.edge_projects;
    
    -- Подсчитать количество рёбер с проектами
    SELECT COUNT(DISTINCT edge_id) INTO edges_with_projects FROM public.edge_projects;
    
    -- Подсчитать количество уникальных проектов в связях
    SELECT COUNT(DISTINCT project_id) INTO projects_in_relations FROM public.edge_projects;
    
    RAISE NOTICE 'Результаты миграции:';
    RAISE NOTICE '  Всего связей проект-ребро: %', total_relations;
    RAISE NOTICE '  Рёбер с проектами: %', edges_with_projects;
    RAISE NOTICE '  Уникальных проектов в связях: %', projects_in_relations;
END $$;
