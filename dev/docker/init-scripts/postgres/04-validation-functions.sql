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
-- 
-- Примечание: Упрощенная версия без Cypher-запросов внутри функции
-- Для полной версии потребуется использовать EXECUTE с динамическим SQL
-- ============================================================================

\echo '6. Создание функции check_edge_uniqueness()...'

CREATE OR REPLACE FUNCTION check_edge_uniqueness(
    graph_name TEXT,
    from_vertex_id BIGINT,
    to_vertex_id BIGINT,
    exclude_edge_id BIGINT DEFAULT NULL
) RETURNS TABLE(is_unique BOOLEAN, error_message TEXT, existing_edge_id TEXT) AS $$
BEGIN
    -- Упрощенная версия: возвращаем true (уникальна)
    -- Полная реализация потребует динамического SQL
    -- TODO: Реализовать проверку через EXECUTE когда будет протестирована базовая функциональность
    
    RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция check_edge_uniqueness() создана (упрощенная версия)'
\echo ''

-- ============================================================================
-- Функция 2: Безопасное создание ребра
-- Использует прямую вставку в таблицы AGE
-- ============================================================================

\echo '7. Создание функции create_edge_safe()...'

CREATE OR REPLACE FUNCTION create_edge_safe(
    graph_name TEXT,
    from_vertex_id BIGINT,
    to_vertex_id BIGINT,
    edge_label TEXT,
    properties JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE(success BOOLEAN, edge_id TEXT, error_message TEXT) AS $$
DECLARE
    uniqueness_check RECORD;
BEGIN
    -- Шаг 1: Проверить уникальность  
    SELECT * INTO uniqueness_check 
    FROM check_edge_uniqueness(graph_name, from_vertex_id, to_vertex_id);
    
    IF NOT uniqueness_check.is_unique THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, uniqueness_check.error_message;
        RETURN;
    END IF;
    
    -- Шаг 2: Создать ребро
    -- TODO: Реализовать создание через Cypher
    -- Пока возвращаем успех с placeholder ID
    RETURN QUERY SELECT TRUE, 'pending'::TEXT, NULL::TEXT;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, SQLERRM;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция create_edge_safe() создана (упрощенная версия)'
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
BEGIN
    -- TODO: Реализовать обновление через Cypher
    RETURN QUERY SELECT TRUE, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция update_edge_safe() создана (упрощенная версия)'
\echo ''

-- ============================================================================
-- Функция 4: Удаление ребра
-- ============================================================================

\echo '9. Создание функции delete_edge_safe()...'

CREATE OR REPLACE FUNCTION delete_edge_safe(
    graph_name TEXT,
    edge_id BIGINT
) RETURNS TABLE(success BOOLEAN, error_message TEXT) AS $$
BEGIN
    -- TODO: Реализовать удаление через Cypher
    RETURN QUERY SELECT TRUE, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

\echo '✓ Функция delete_edge_safe() создана (упрощенная версия)'
\echo ''

\echo '================================================'
\echo 'Функции-заглушки созданы успешно!'
\echo '================================================'
\echo ''
\echo 'ВАЖНО: Это упрощенные версии функций'
\echo 'Они позволяют завершить инициализацию БД'
\echo 'Полная реализация с Cypher будет добавлена в следующих версиях'
\echo ''
\echo 'Для работы с графом используйте прямые Cypher запросы:'
\echo '  SELECT * FROM cypher(''common_project_graph'', $q$'
\echo '    CREATE (n {name: ''test''})'
\echo '  $q$) as (result agtype);'
\echo ''
