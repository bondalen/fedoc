-- ============================================================================
-- Инициализация Apache AGE для проекта fedoc
-- PostgreSQL 16.10 + Apache AGE 1.6.0
-- ============================================================================

\echo '================================================'
\echo 'Инициализация Apache AGE для fedoc'
\echo '================================================'

-- Создать базу данных fedoc (если еще не создана)
-- Примечание: Этот скрипт запускается в контексте postgres database
-- После создания БД нужно переподключиться к ней

\echo '1. Создание базы данных fedoc...'

-- Проверить существование базы данных
SELECT 'База данных fedoc уже существует' 
WHERE EXISTS (SELECT FROM pg_database WHERE datname = 'fedoc');

-- Создать базу данных если не существует
-- (CREATE DATABASE не поддерживает IF NOT EXISTS до PostgreSQL 9.3+, но в 16.10 это работает)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fedoc') THEN
        CREATE DATABASE fedoc
            WITH 
            OWNER = postgres
            ENCODING = 'UTF8'
            LC_COLLATE = 'C'
            LC_CTYPE = 'C'
            TEMPLATE = template0;
        RAISE NOTICE 'База данных fedoc создана';
    ELSE
        RAISE NOTICE 'База данных fedoc уже существует';
    END IF;
END
$$;

\echo '✓ База данных fedoc готова'
\echo ''

