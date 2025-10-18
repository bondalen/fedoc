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
    query TEXT;
    result_row RECORD;
BEGIN
    -- Построить Cypher запрос для поиска дублирующих рёбер
    -- Проверяем оба направления: (from)-[]->(to) и (to)-[]->(from)
    query := format(
        'SELECT * FROM cypher(%L, $$ 
            MATCH (a)-[e]->(b)
            WHERE (id(a) = %s AND id(b) = %s)
               OR (id(a) = %s AND id(b) = %s)
        ',
        graph_name,
        from_vertex_id,
        to_vertex_id,
        to_vertex_id,
        from_vertex_id
    );
    
    -- Добавить фильтр для исключения текущего ребра (при обновлении)
    IF exclude_edge_id IS NOT NULL THEN
        query := query || format(' AND id(e) <> %s', exclude_edge_id);
    END IF;
    
    query := query || ' RETURN id(e) as edge_id, id(a) as from_id, id(b) as to_id LIMIT 1
        $$) as (edge_id agtype, from_id agtype, to_id agtype)';
    
    -- Выполнить запрос
    EXECUTE query INTO result_row;
    
    -- Если найден дубликат
    IF result_row.edge_id IS NOT NULL THEN
        -- Определить направление дубликата
        IF result_row.from_id::text::bigint = from_vertex_id THEN
            error_message := format(
                'Связь между вершинами %s и %s уже существует (прямая связь, ID: %s)',
                from_vertex_id,
                to_vertex_id,
                result_row.edge_id::text::bigint
            );
        ELSE
            error_message := format(
                'Связь между вершинами %s и %s уже существует (обратная связь, ID: %s)',
                from_vertex_id,
                to_vertex_id,
                result_row.edge_id::text::bigint
            );
        END IF;
        
        RETURN QUERY SELECT FALSE, error_message, result_row.edge_id::text::bigint;
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
    query TEXT;
    result_row RECORD;
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
    query := format(
        'SELECT * FROM cypher(%L, $$
            MATCH (a), (b)
            WHERE id(a) = %s AND id(b) = %s
            CREATE (a)-[e:%s %s]->(b)
            RETURN id(e) as edge_id
        $$) as (edge_id agtype)',
        graph_name,
        from_vertex_id,
        to_vertex_id,
        edge_label,
        properties::text
    );
    
    EXECUTE query INTO result_row;
    
    -- Вернуть успех
    RETURN QUERY SELECT TRUE, result_row.edge_id::text::bigint, NULL::TEXT;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Обработка ошибок
        RETURN QUERY SELECT FALSE, NULL::BIGINT, SQLERRM;
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
    new_from_vertex_id BIGINT DEFAULT NULL,
    new_to_vertex_id BIGINT DEFAULT NULL,
    new_properties JSONB DEFAULT NULL
) RETURNS TABLE(success BOOLEAN, error_message TEXT) AS $$
DECLARE
    current_from BIGINT;
    current_to BIGINT;
    final_from BIGINT;
    final_to BIGINT;
    uniqueness_check RECORD;
    query TEXT;
BEGIN
    -- Шаг 1: Получить текущие значения from/to
    query := format(
        'SELECT * FROM cypher(%L, $$
            MATCH (a)-[e]->(b)
            WHERE id(e) = %s
            RETURN id(a) as from_id, id(b) as to_id
        $$) as (from_id agtype, to_id agtype)',
        graph_name,
        edge_id
    );
    
    EXECUTE query INTO current_from, current_to;
    
    IF current_from IS NULL THEN
        RETURN QUERY SELECT FALSE, format('Ребро с ID %s не найдено', edge_id);
        RETURN;
    END IF;
    
    -- Определить финальные значения
    final_from := COALESCE(new_from_vertex_id, current_from);
    final_to := COALESCE(new_to_vertex_id, current_to);
    
    -- Шаг 2: Проверить уникальность (если узлы изменились)
    IF (final_from <> current_from OR final_to <> current_to) THEN
        SELECT * INTO uniqueness_check 
        FROM check_edge_uniqueness(graph_name, final_from, final_to, edge_id);
        
        IF NOT uniqueness_check.is_unique THEN
            RETURN QUERY SELECT FALSE, uniqueness_check.error_message;
            RETURN;
        END IF;
    END IF;
    
    -- Шаг 3: Обновить ребро
    -- Примечание: В AGE нельзя напрямую изменить узлы ребра
    -- Нужно удалить старое и создать новое, либо обновить только properties
    IF new_properties IS NOT NULL THEN
        query := format(
            'SELECT * FROM cypher(%L, $$
                MATCH ()-[e]->()
                WHERE id(e) = %s
                SET e = %s
                RETURN id(e)
            $$) as (edge_id agtype)',
            graph_name,
            edge_id,
            new_properties::text
        );
        
        EXECUTE query;
    END IF;
    
    RETURN QUERY SELECT TRUE, NULL::TEXT;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN QUERY SELECT FALSE, SQLERRM;
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
    query TEXT;
BEGIN
    query := format(
        'SELECT * FROM cypher(%L, $$
            MATCH ()-[e]->()
            WHERE id(e) = %s
            DELETE e
            RETURN id(e)
        $$) as (edge_id agtype)',
        graph_name,
        edge_id
    );
    
    EXECUTE query;
    
    RETURN QUERY SELECT TRUE, NULL::TEXT;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN QUERY SELECT FALSE, SQLERRM;
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

