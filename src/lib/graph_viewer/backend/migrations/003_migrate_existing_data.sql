-- Миграция 003: Миграция существующих данных проектов в рёбрах
-- Дата: 2025-01-20
-- Описание: Перенос данных из поля properties.projects в нормализованную структуру

-- Временная функция для извлечения проектов из JSON
CREATE OR REPLACE FUNCTION extract_projects_from_properties(properties JSONB)
RETURNS TEXT[] AS $$
DECLARE
    projects_array JSONB;
    result TEXT[] := '{}';
    project_item JSONB;
BEGIN
    -- Проверить наличие поля projects
    IF properties ? 'projects' THEN
        projects_array := properties->'projects';
        
        -- Если это массив
        IF jsonb_typeof(projects_array) = 'array' THEN
            -- Извлечь все элементы массива
            FOR project_item IN SELECT jsonb_array_elements(projects_array)
            LOOP
                -- Если элемент - строка, добавить в результат
                IF jsonb_typeof(project_item) = 'string' THEN
                    result := result || jsonb_extract_path_text(project_item);
                END IF;
            END LOOP;
        END IF;
    END IF;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Основная миграция данных
DO $$
DECLARE
    edge_record RECORD;
    project_key TEXT;
    projects_list TEXT[];
    project_count INTEGER := 0;
    total_edges INTEGER := 0;
BEGIN
    RAISE NOTICE 'Начинаем миграцию данных проектов в рёбрах...';
    
    -- Подсчитать общее количество рёбер для обработки
    SELECT COUNT(*) INTO total_edges
    FROM common_project_graph.project_relation 
    WHERE properties->>'projects' IS NOT NULL;
    
    RAISE NOTICE 'Найдено % рёбер с полем projects', total_edges;
    
    -- Пройти по всем рёбрам с полем projects
    FOR edge_record IN 
        SELECT id, properties 
        FROM common_project_graph.project_relation 
        WHERE properties->>'projects' IS NOT NULL
    LOOP
        -- Извлечь список проектов
        projects_list := extract_projects_from_properties(edge_record.properties);
        
        -- Добавить каждый проект в нормализованную структуру
        FOR project_key IN SELECT unnest(projects_list)
        LOOP
            BEGIN
                -- Добавить связь в нормализованную таблицу
                PERFORM ag_catalog.add_project_to_edge(
                    edge_record.id,
                    project_key,
                    'participant',  -- роль по умолчанию
                    1.0,            -- вес по умолчанию
                    'migration',    -- создано миграцией
                    jsonb_build_object(
                        'migrated_from', 'properties.projects',
                        'migration_date', NOW()
                    )
                );
                
                project_count := project_count + 1;
                
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при добавлении проекта % к ребру %: %', 
                    project_key, edge_record.id, SQLERRM;
            END;
        END LOOP;
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

-- Удалить временную функцию
DROP FUNCTION IF EXISTS extract_projects_from_properties(JSONB);
