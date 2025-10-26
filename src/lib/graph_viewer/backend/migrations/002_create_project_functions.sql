-- Миграция 002: Создание функций для работы с нормализованными проектами
-- Дата: 2025-10-26
-- Описание: Функции для получения, добавления и управления проектами в рёбрах

-- Функция получения проектов ребра с полной информацией
CREATE OR REPLACE FUNCTION ag_catalog.get_edge_projects_enriched(p_edge_id BIGINT)
RETURNS TABLE(
    project_info JSONB,
    role VARCHAR(50),
    weight DECIMAL(3,2),
    created_at TIMESTAMP,
    created_by VARCHAR(100),
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jsonb_build_object(
            'id', p.key,
            'name', p.name,
            'description', p.description,
            'created_at', p.created_at,
            'updated_at', p.updated_at,
            'data', p.data
        ) as project_info,
        ep.role,
        ep.weight,
        ep.created_at,
        ep.created_by,
        ep.metadata
    FROM public.edge_projects ep
    JOIN public.projects p ON ep.project_id = p.id
    WHERE ep.edge_id = p_edge_id
    ORDER BY ep.weight DESC, p.name;
END;
$$ LANGUAGE plpgsql;

-- Функция добавления проекта к ребру
CREATE OR REPLACE FUNCTION ag_catalog.add_project_to_edge(
    p_edge_id BIGINT,
    p_project_key VARCHAR(50),
    p_role VARCHAR(50) DEFAULT 'participant',
    p_weight DECIMAL(3,2) DEFAULT 1.0,
    p_created_by VARCHAR(100) DEFAULT 'system',
    p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS BOOLEAN AS $$
DECLARE
    v_project_id INTEGER;
BEGIN
    -- Получить ID проекта по ключу
    SELECT id INTO v_project_id 
    FROM public.projects 
    WHERE key = p_project_key;
    
    IF v_project_id IS NULL THEN
        RAISE EXCEPTION 'Project % not found', p_project_key;
    END IF;
    
    -- Добавить связь
    INSERT INTO public.edge_projects (edge_id, project_id, role, weight, created_by, metadata)
    VALUES (p_edge_id, v_project_id, p_role, p_weight, p_created_by, p_metadata)
    ON CONFLICT (edge_id, project_id) DO UPDATE SET
        role = EXCLUDED.role,
        weight = EXCLUDED.weight,
        metadata = EXCLUDED.metadata;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Функция удаления проекта из ребра
CREATE OR REPLACE FUNCTION ag_catalog.remove_project_from_edge(
    p_edge_id BIGINT,
    p_project_key VARCHAR(50)
) RETURNS BOOLEAN AS $$
DECLARE
    v_project_id INTEGER;
BEGIN
    -- Получить ID проекта по ключу
    SELECT id INTO v_project_id 
    FROM public.projects 
    WHERE key = p_project_key;
    
    IF v_project_id IS NULL THEN
        RAISE EXCEPTION 'Project % not found', p_project_key;
    END IF;
    
    -- Удалить связь
    DELETE FROM public.edge_projects 
    WHERE edge_id = p_edge_id AND project_id = v_project_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Функция получения всех рёбер проекта
CREATE OR REPLACE FUNCTION ag_catalog.get_project_edges(p_project_key VARCHAR(50))
RETURNS TABLE(
    edge_id BIGINT,
    start_id BIGINT,
    end_id BIGINT,
    properties JSONB,
    role VARCHAR(50),
    weight DECIMAL(3,2),
    created_at TIMESTAMP
) AS $$
DECLARE
    v_project_id INTEGER;
BEGIN
    -- Получить ID проекта по ключу
    SELECT id INTO v_project_id 
    FROM public.projects 
    WHERE key = p_project_key;
    
    IF v_project_id IS NULL THEN
        RAISE EXCEPTION 'Project % not found', p_project_key;
    END IF;
    
    RETURN QUERY
    SELECT 
        e.id as edge_id,
        e.start_id,
        e.end_id,
        e.properties,
        ep.role,
        ep.weight,
        ep.created_at
    FROM ag_catalog.ag_edge e
    JOIN public.edge_projects ep ON e.id = ep.edge_id
    WHERE ep.project_id = v_project_id
    ORDER BY ep.weight DESC, e.id;
END;
$$ LANGUAGE plpgsql;

-- Комментарии к функциям
COMMENT ON FUNCTION ag_catalog.get_edge_projects_enriched(BIGINT) IS 'Получить все проекты ребра с полной информацией';
COMMENT ON FUNCTION ag_catalog.add_project_to_edge(BIGINT, VARCHAR, VARCHAR, DECIMAL, VARCHAR, JSONB) IS 'Добавить проект к ребру';
COMMENT ON FUNCTION ag_catalog.remove_project_from_edge(BIGINT, VARCHAR) IS 'Удалить проект из ребра';
COMMENT ON FUNCTION ag_catalog.get_project_edges(VARCHAR) IS 'Получить все рёбра проекта';
