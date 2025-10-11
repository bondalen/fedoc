# Docker конфигурация для fedoc

Развертывание трех баз данных на production сервере через Docker Compose.

## 🗄️ Базы данных

| БД | Назначение | RAM | Порт | Режим |
|----|-----------|-----|------|-------|
| **ArangoDB** | fedoc (Multi-Model) | ~600 MB | 8529 | 🎯 По требованию |
| **PostgreSQL** | Общие проекты | ~400 MB | 5432 | 🎯 По требованию |
| **MS SQL Server** | FEMSQ и др. | ~1.5-2 GB | 1433 | 🎯 По требованию |

**Все БД запускаются по требованию** - максимальная гибкость и экономия ресурсов!

## 🚀 Быстрый старт

### 1. Настройка

```bash
# Скопировать шаблон .env
cp .env.example .env

# Установить пароли
nano .env

# Установить права
chmod 600 .env
chmod +x db-manager.sh
```

### 2. Запуск

```bash
# Базовые БД (ArangoDB + PostgreSQL)
./db-manager.sh start

# Проверить статус
./db-manager.sh status
```

### 3. Доступ

```bash
# Показать информацию для подключения
./db-manager.sh connections

# Web UI ArangoDB (через SSH туннель)
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N
# Затем: http://localhost:8529
```

## 📁 Структура

```
docker/
├── docker-compose.prod.yml   # Конфигурация всех БД
├── .env.example               # Шаблон паролей
├── .env                       # Реальные пароли (не в git!)
├── db-manager.sh              # Скрипт управления БД
├── DEPLOYMENT.md              # Полная инструкция
├── README.md                  # Этот файл
│
├── init-scripts/              # Скрипты инициализации
│   ├── arango/               # JavaScript для ArangoDB
│   ├── postgres/             # SQL для PostgreSQL
│   └── mssql/                # SQL для MS SQL Server
│
├── arango-data/              # Данные ArangoDB (не в git!)
├── postgres-data/            # Данные PostgreSQL (не в git!)
├── mssql-data/               # Данные MS SQL (не в git!)
└── backups/                  # Бэкапы БД (не в git!)
```

## 🎮 Управление

### Запуск (все БД по требованию)
```bash
./db-manager.sh start           # ArangoDB + PostgreSQL
./db-manager.sh start-arango    # Только ArangoDB
./db-manager.sh start-postgres  # Только PostgreSQL
./db-manager.sh start-mssql     # Только MS SQL
./db-manager.sh start-all       # Все БД сразу
```

### Остановка
```bash
./db-manager.sh stop            # Остановить все
./db-manager.sh stop-arango     # Остановить ArangoDB
./db-manager.sh stop-postgres   # Остановить PostgreSQL
./db-manager.sh stop-mssql      # Остановить MS SQL
```

### Информация
```bash
./db-manager.sh status          # Статус и ресурсы
./db-manager.sh connections     # Данные для подключения
./db-manager.sh monitor         # Мониторинг в реальном времени
./db-manager.sh logs <service>  # Логи
```

### Бэкапы
```bash
./db-manager.sh backup all      # Все БД
./db-manager.sh backup arangodb # Только ArangoDB
```

### Справка
```bash
./db-manager.sh help
```

## 📖 Документация

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Полная инструкция по развертыванию
- **[docker-compose.prod.yml](docker-compose.prod.yml)** - Конфигурация Docker

## 🔧 Рекомендуемые режимы (запуск по требованию)

### Режим 0: Минимальный
```bash
# Ничего не запущено - 0 MB RAM
```

### Режим 1: Работа с fedoc
```bash
./db-manager.sh start-arango  # Только ArangoDB
```
Потребление: ~600 MB RAM

### Режим 2: Работа с PostgreSQL проектами
```bash
./db-manager.sh start-postgres  # Только PostgreSQL
```
Потребление: ~400 MB RAM

### Режим 3: Комбинированный
```bash
./db-manager.sh start  # ArangoDB + PostgreSQL
```
Потребление: ~1 GB RAM

### Режим 4: С FEMSQ
```bash
./db-manager.sh start-mssql  # Добавить MS SQL
# Работа...
./db-manager.sh stop-mssql   # Освободить RAM
```

## 🔒 Безопасность

- Все БД доступны только с localhost (127.0.0.1)
- Пароли в .env (права 600, не в git)
- Данные в volumes (не в git)
- Порты закрыты для внешнего доступа

## 📊 Потребление ресурсов

| Конфигурация | RAM | Свободно |
|-------------|-----|----------|
| ArangoDB + PostgreSQL | ~1 GB | ~2.8 GB ✅ |
| + MS SQL Server | ~2.6 GB | ~800 MB ⚠️ |

## 🆘 Troubleshooting

См. раздел [Troubleshooting в DEPLOYMENT.md](DEPLOYMENT.md#8-troubleshooting)

---

**Версия:** 1.0.0  
**Дата:** 2025-10-11

