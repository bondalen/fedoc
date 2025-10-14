# Скрипты инициализации MS SQL Server

Поместите сюда SQL файлы для автоматического выполнения при первом запуске MS SQL Server.

## Примеры

### Создание базы данных
```sql
-- 01-create-database.sql
CREATE DATABASE MyProject;
GO
```

### Создание таблиц
```sql
-- 02-create-schema.sql
USE MyProject;
GO

CREATE TABLE Users (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL,
    CreatedAt DATETIME2 DEFAULT GETDATE()
);
GO
```

Файлы выполняются в алфавитном порядке.

