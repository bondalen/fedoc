-- ============================================================================
-- Создание графа common_project_graph в Apache AGE
-- База данных: fedoc
-- ============================================================================

\echo '================================================'
\echo 'Создание графа common_project_graph'
\echo '================================================'

-- Подключиться к базе данных fedoc
\c fedoc

-- Установить search_path
SET search_path = ag_catalog, "$user", public;

\echo '4. Создание графа common_project_graph...'

-- Создать граф
-- В AGE графы создаются функцией create_graph()
SELECT ag_catalog.create_graph('common_project_graph');

\echo '✓ Граф common_project_graph создан'
\echo ''

-- Информация о графе
\echo '5. Информация о созданном графе:'
SELECT * FROM ag_catalog.ag_graph WHERE name = 'common_project_graph';

\echo ''
\echo '================================================'
\echo 'Инициализация AGE завершена успешно!'
\echo '================================================'
\echo ''
\echo 'Следующие шаги:'
\echo '  1. Создать функции валидации'
\echo '  2. Мигрировать данные из ArangoDB'
\echo '  3. Тестировать запросы Cypher'
\echo ''

