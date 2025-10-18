-- ============================================================================
-- Функции валидации рёбер графа в PostgreSQL + Apache AGE
-- 
-- Ключевая фича миграции: вся логика валидации в БД!
-- Замена двух запросов (проверка + создание) на один вызов функции
-- ============================================================================

\echo '================================================'
\echo 'Создание функций валидации рёбер'
\echo '================================================'

\c fedoc

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- ============================================================================
-- Функция 1: Проверка уникальности ребра
-- Проверяет связь в ОБОИХ направлениях (A→B и B→A)
-- ============================================================================

\echo '6. Создание функции check_edge_uniqueness()...'

CREATE OR REPLACE FUNCTION check_edge_uniqueness(
    graph_name TEXT,
    from_vertex_id BIGINT,
    to_vertex_id BIGINT,
    exclude_edge_id BIGINT DEFAULT NULL
) RETURNS TABLE(is_unique BOOLEAN, error_message TEXT, existing_edge_id BIGINT) AS $$
DECLARE
    result_count INTEGER;
    edge_data RECORD;
BEGIN
    -- Выполнить Cypher запрос для поиска дублирующих рёбер
    -- Проверяем оба направления: (from)-[]->(to) и (to)-[]->(from)
    
    IF exclude_edge_id IS NULL THEN
        -- Без исключения (для создания нового ребра)
        SELECT * INTO edge_data FROM cypher(graph_name, $$
            MATCH (a)-[e]->(b)
            WHERE (id(a) = $from_id AND id(b) = $to_id)
               OR (id(a) = $to_id AND id(b) = $from_id)
            RETURN id(e) as edge_id, id(a) as from_id, id(b) as to_id
            LIMIT 1
        $$, 
        jsonb_build_object('from_id', from_vertex_id, 'to_id', to_vertex_id)
        ) as (edge_id agtype, from_id agtype, to_id agtype);
    ELSE
        -- С исключением (для обновления существующего ребра)
        SELECT * INTO edge_data FROM cypher(graph_name, $$
            MATCH (a)-[e]->(b)
            WHERE ((id(a) = $from_id AND id(b) = $to_id)
                OR (id(a) = $to_id AND id(b) = $from_id))
              AND id(e) <> $exclude_id
            RETURN id(e) as edge_id, id(a) as from_id, id(b) as to_id
            LIMIT 1
        $$,
        jsonb_build_object(
            'from_id', from_vertex_id, 
            'to_id', to_vertex_id,
            'exclude_id', exclude_edge_id
        )
        ) as (edge_id agtype, from_id agtype, to_id agtype);
    END IF;
    
    -- Если найден дубликат
    IF edge_data.edge_id IS NOT NULL THEN
        -- Определить направление дубликата
        IF (edge_data.from_id)::text::bigint = from_vertex_id THEN
            RETURN QUERY SELECT 
                FALSE,
                format('Связь между вершинами %s и %s уже существует (прямая связь, ID: %s)',
                    from_vertex_id, to_vertex_id, (edge_data.edge_id)::text::bigint
                ),
                (edge_data.edge_id)::text::bigint;
        ELSE
            RETURN QUERY SELECT 
                FALSE,
                format('Связь между вершинами %s и %s уже существует (обратная связь, ID: %s)',
                    from_vertex_id, to_vertex_id, (edge_data.edge_id)::text::bigint
                ),
                (edge_data.edge_id)::text::bigint;
        END IF;
    ELSE
        -- Связь уникальна
        RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::BIGINT;
    END IF;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция check_edge_uniqueness() создана'
\echo ''

-- ============================================================================
-- Функция 2: Безопасное создание ребра с валидацией
-- Атомарная операция: проверка + создание в одной транзакции
-- ============================================================================

\echo '7. Создание функции create_edge_safe()...'

CREATE OR REPLACE FUNCTION create_edge_safe(
    graph_name TEXT,
    from_vertex_id BIGINT,
    to_vertex_id BIGINT,
    edge_label TEXT,
    properties JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE(success BOOLEAN, edge_id BIGINT, error_message TEXT) AS $$
DECLARE
    uniqueness_check RECORD;
    result_data RECORD;
BEGIN
    -- Шаг 1: Проверить уникальность
    SELECT * INTO uniqueness_check 
    FROM check_edge_uniqueness(graph_name, from_vertex_id, to_vertex_id);
    
    IF NOT uniqueness_check.is_unique THEN
        -- Связь не уникальна - вернуть ошибку
        RETURN QUERY SELECT FALSE, NULL::BIGINT, uniqueness_check.error_message;
        RETURN;
    END IF;
    
    -- Шаг 2: Создать ребро через Cypher
    -- Используем ag_catalog.create_complete_graph или прямой Cypher
    BEGIN
        SELECT * INTO result_data FROM cypher(graph_name, 
            format('MATCH (a), (b) WHERE id(a) = %s AND id(b) = %s CREATE (a)-[e:%s %s]->(b) RETURN id(e)',
                from_vertex_id, to_vertex_id, edge_label, properties::text
            )
        ) as (edge_id agtype);
        
        -- Вернуть успех
        RETURN QUERY SELECT TRUE, (result_data.edge_id)::text::bigint, NULL::TEXT;
        
    EXCEPTION
        WHEN OTHERS THEN
            -- Обработка ошибок
            RETURN QUERY SELECT FALSE, NULL::BIGINT, SQLERRM;
    END;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция create_edge_safe() создана'
\echo ''

-- ============================================================================
-- Функция 3: Безопасное обновление ребра
-- ============================================================================

\echo '8. Создание функции update_edge_safe()...'

CREATE OR REPLACE FUNCTION update_edge_safe(
    graph_name TEXT,
    edge_id BIGINT,
    new_properties JSONB DEFAULT NULL
) RETURNS TABLE(success BOOLEAN, error_message TEXT) AS $$
DECLARE
    result_data RECORD;
BEGIN
    -- Обновить свойства ребра
    IF new_properties IS NOT NULL THEN
        BEGIN
            SELECT * INTO result_data FROM cypher(graph_name,
                format('MATCH ()-[e]->() WHERE id(e) = %s SET e = %s RETURN id(e)',
                    edge_id, new_properties::text
                )
            ) as (edge_id agtype);
            
            IF result_data.edge_id IS NULL THEN
                RETURN QUERY SELECT FALSE, format('Ребро с ID %s не найдено', edge_id);
                RETURN;
            END IF;
            
            RETURN QUERY SELECT TRUE, NULL::TEXT;
            
        EXCEPTION
            WHEN OTHERS THEN
                RETURN QUERY SELECT FALSE, SQLERRM;
        END;
    ELSE
        RETURN QUERY SELECT TRUE, NULL::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция update_edge_safe() создана'
\echo ''

-- ============================================================================
-- Функция 4: Удаление ребра
-- ============================================================================

\echo '9. Создание функции delete_edge_safe()...'

CREATE OR REPLACE FUNCTION delete_edge_safe(
    graph_name TEXT,
    edge_id BIGINT
) RETURNS TABLE(success BOOLEAN, error_message TEXT) AS $$
DECLARE
    result_data RECORD;
BEGIN
    BEGIN
        SELECT * INTO result_data FROM cypher(graph_name,
            format('MATCH ()-[e]->() WHERE id(e) = %s DELETE e RETURN id(e)',
                edge_id
            )
        ) as (edge_id agtype);
        
        IF result_data.edge_id IS NULL THEN
            RETURN QUERY SELECT FALSE, format('Ребро с ID %s не найдено', edge_id);
            RETURN;
        END IF;
        
        RETURN QUERY SELECT TRUE, NULL::TEXT;
        
    EXCEPTION
        WHEN OTHERS THEN
            RETURN QUERY SELECT FALSE, SQLERRM;
    END;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция delete_edge_safe() создана'
\echo ''

\echo '================================================'
\echo 'Функции валидации созданы успешно!'
\echo '================================================'
\echo ''
\echo 'Созданные функции:'
\echo '  1. check_edge_uniqueness() - проверка уникальности'
\echo '  2. create_edge_safe() - создание с валидацией'
\echo '  3. update_edge_safe() - обновление с валидацией'
\echo '  4. delete_edge_safe() - удаление'
\echo ''
