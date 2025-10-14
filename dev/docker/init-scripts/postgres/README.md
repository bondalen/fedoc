# Скрипты инициализации PostgreSQL

Поместите сюда SQL файлы для автоматического выполнения при первом запуске PostgreSQL.

## Примеры

### Создание базы данных
```sql
-- 01-create-database.sql
CREATE DATABASE myproject;
```

### Создание схемы
```sql
-- 02-create-schema.sql
\c myproject
CREATE SCHEMA IF NOT EXISTS app;
CREATE TABLE app.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Файлы выполняются в алфавитном порядке.

