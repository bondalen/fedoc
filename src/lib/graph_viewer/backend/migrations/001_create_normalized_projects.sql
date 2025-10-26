-- Миграция 001: Создание нормализованной структуры для проектов в рёбрах
-- Дата: 2025-10-26
-- Описание: Создание таблицы edge_projects для связи рёбер с проектами

-- Создание таблицы связи рёбер с проектами
CREATE TABLE IF NOT EXISTS public.edge_projects (
    id SERIAL PRIMARY KEY,
    edge_id BIGINT NOT NULL,
    project_id INTEGER REFERENCES public.projects(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'participant', -- роль проекта в связи
    weight DECIMAL(3,2) DEFAULT 1.0,       -- вес связи для проекта
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system', -- кто создал связь
    metadata JSONB DEFAULT '{}'::JSONB,    -- дополнительные метаданные
    UNIQUE(edge_id, project_id)
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_edge_projects_edge_id ON public.edge_projects(edge_id);
CREATE INDEX IF NOT EXISTS idx_edge_projects_project_id ON public.edge_projects(project_id);
CREATE INDEX IF NOT EXISTS idx_edge_projects_role ON public.edge_projects(role);
CREATE INDEX IF NOT EXISTS idx_edge_projects_created_at ON public.edge_projects(created_at);

-- Комментарии к таблице и колонкам
COMMENT ON TABLE public.edge_projects IS 'Связь рёбер графа с проектами - нормализованная структура';
COMMENT ON COLUMN public.edge_projects.edge_id IS 'ID ребра в Apache AGE графе';
COMMENT ON COLUMN public.edge_projects.project_id IS 'ID проекта из таблицы projects';
COMMENT ON COLUMN public.edge_projects.role IS 'Роль проекта в связи (participant, owner, consumer, etc.)';
COMMENT ON COLUMN public.edge_projects.weight IS 'Вес связи для проекта (0.0-1.0)';
COMMENT ON COLUMN public.edge_projects.created_by IS 'Пользователь или система, создавшая связь';
COMMENT ON COLUMN public.edge_projects.metadata IS 'Дополнительные метаданные связи в JSON формате';
