# Развертывание баз данных fedoc на production сервере

**Сервер:** 176.108.244.252  
**Ресурсы:** 2 CPU, 3.8 GB RAM, 30 GB Disk  
**ОС:** Ubuntu 22.04 LTS  
**Docker:** 28.2.2

---

## 📋 Содержание

1. [Подготовка сервера](#1-подготовка-сервера)
2. [Клонирование репозитория](#2-клонирование-репозитория)
3. [Настройка конфигурации](#3-настройка-конфигурации)
4. [Запуск баз данных](#4-запуск-баз-данных)
5. [Проверка работы](#5-проверка-работы)
6. [Использование](#6-использование)
7. [Мониторинг и обслуживание](#7-мониторинг-и-обслуживание)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Подготовка сервера

### 1.1 Подключение к серверу

```bash
ssh user1@176.108.244.252
```

### 1.2 Удаление старых неиспользуемых образов

```bash
# Проверить старые образы
docker images

# Удалить старый образ openjdk (если есть)
docker rmi openjdk:21-slim

# Очистить неиспользуемые образы
docker image prune -a -f

# Освободить место
docker system prune -f
```

**Результат:** Освобождено ~439 MB + дополнительное место

### 1.3 Проверка ресурсов

```bash
# Память
free -h

# Диск
df -h

# CPU
lscpu | grep "^CPU(s):"

# Docker версия
docker --version
```

**Ожидаемые значения:**
- RAM: ~3.4 GB свободно ✓
- Disk: ~23 GB свободно ✓
- CPU: 2 cores ✓
- Docker: 28.2.2+ ✓

---

## 2. Клонирование репозитория

```bash
# Перейти в домашнюю директорию
cd /home/user1

# Клонировать репозиторий
git clone https://github.com/bondalen/fedoc.git

# Перейти в директорию docker
cd fedoc/docker
```

---

## 3. Настройка конфигурации

### 3.1 Создать .env файл с паролями

```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать файл (установить надежные пароли)
nano .env
```

**Требования к паролям:**

**ArangoDB:**
- Любой сложный пароль

**PostgreSQL:**
- Любой сложный пароль

**MS SQL Server:**
- Минимум 8 символов
- Заглавные буквы (A-Z)
- Строчные буквы (a-z)
- Цифры (0-9)
- Спецсимволы (!@#$%^&*)
- Пример: `MyStr0ng@Pass2025`

### 3.2 Установить права на .env

```bash
chmod 600 .env
```

### 3.3 Создать директории для данных

```bash
# Создаются автоматически, но можно создать вручную
mkdir -p arango-data arango-apps postgres-data mssql-data backups
```

### 3.4 Сделать скрипт управления исполняемым

```bash
chmod +x db-manager.sh
```

---

## 4. Запуск баз данных

### 4.1 Запуск базовых БД (рекомендуется для ежедневной работы)

```bash
./db-manager.sh start
```

**Запускается:**
- ✅ ArangoDB (порт 8529)
- ✅ PostgreSQL (порт 5432)

**Потребление:** ~600-1000 MB RAM  
**Свободно:** ~2.4-2.8 GB

### 4.2 Запуск MS SQL Server (по требованию)

```bash
./db-manager.sh start-mssql
```

**Запускается:**
- ✅ MS SQL Server (порт 1433)

**Потребление:** +1.5-2 GB RAM  
**Итого:** ~2.6-3 GB RAM

### 4.3 Запуск всех БД сразу (опционально)

```bash
./db-manager.sh start-all
```

---

## 5. Проверка работы

### 5.1 Проверить статус контейнеров

```bash
./db-manager.sh status
```

**Ожидаемый вывод:**
```
NAME              STATUS          PORTS
fedoc-arango      Up 2 minutes    127.0.0.1:8529->8529/tcp
fedoc-postgres    Up 2 minutes    127.0.0.1:5432->5432/tcp
```

### 5.2 Проверить логи

```bash
# Логи ArangoDB
./db-manager.sh logs arangodb

# Логи PostgreSQL
./db-manager.sh logs postgres

# Логи MS SQL (если запущен)
./db-manager.sh logs mssql
```

### 5.3 Проверить API

```bash
# ArangoDB
curl http://localhost:8529/_api/version

# PostgreSQL
docker exec fedoc-postgres psql -U postgres -c "SELECT version();"

# MS SQL (если запущен)
docker exec fedoc-mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "$MSSQL_PASSWORD" -Q "SELECT @@VERSION"
```

### 5.4 Проверить потребление ресурсов

```bash
# Статус с ресурсами
./db-manager.sh status

# Мониторинг в реальном времени
./db-manager.sh monitor
# (Ctrl+C для выхода)
```

---

## 6. Использование

### 6.1 Получить информацию для подключения

```bash
./db-manager.sh connections
```

### 6.2 Доступ к Web UI ArangoDB

**С локальной машины через SSH туннель:**

```bash
# На вашей локальной машине (WSL2)
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N
```

Затем открыть в браузере: http://localhost:8529

**Логин:**
- User: `root`
- Password: (из .env файла `ARANGO_PASSWORD`)

### 6.3 Подключение из приложений

**ArangoDB:**
```python
from arango import ArangoClient

client = ArangoClient(hosts='http://localhost:8529')
db = client.db('_system', username='root', password='your_password')
```

**PostgreSQL:**
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="postgres",
    user="postgres",
    password="your_password"
)
```

**MS SQL Server:**
```python
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost,1433;'
    'UID=sa;'
    'PWD=your_password'
)
```

---

## 7. Мониторинг и обслуживание

### 7.1 Регулярные задачи

**Ежедневно:**
```bash
# Проверить статус
./db-manager.sh status
```

**Еженедельно:**
```bash
# Создать бэкапы всех БД
./db-manager.sh backup all
```

**Ежемесячно:**
```bash
# Проверить размер данных
du -sh arango-data/ postgres-data/ mssql-data/

# Очистить старые бэкапы (старше 30 дней)
find backups/ -type f -mtime +30 -delete
```

### 7.2 Создание бэкапов

```bash
# Все БД
./db-manager.sh backup all

# Конкретная БД
./db-manager.sh backup arangodb
./db-manager.sh backup postgres
./db-manager.sh backup mssql
```

**Бэкапы сохраняются в:** `./backups/`

### 7.3 Остановка БД

```bash
# Остановить все БД
./db-manager.sh stop

# Остановить только MS SQL (освободить RAM)
./db-manager.sh stop-mssql
```

### 7.4 Обновление образов

```bash
# Остановить контейнеры
./db-manager.sh stop

# Обновить образы
docker-compose -f docker-compose.prod.yml pull

# Запустить с новыми образами
./db-manager.sh start
```

---

## 8. Troubleshooting

### Проблема: Контейнер не запускается

```bash
# Проверить логи
./db-manager.sh logs <service>

# Проверить порты
sudo netstat -tulpn | grep -E '8529|5432|1433'

# Проверить docker
docker ps -a
```

### Проблема: Недостаточно памяти

```bash
# Проверить потребление
free -h
docker stats --no-stream

# Остановить MS SQL если не используется
./db-manager.sh stop-mssql
```

### Проблема: Не могу подключиться к БД

**Проверки:**
1. Контейнер запущен: `docker ps`
2. Порт открыт: `netstat -tulpn | grep <port>`
3. Правильный пароль в .env
4. Подключение через 127.0.0.1 (не через внешний IP)

### Проблема: Потерян пароль

```bash
# Посмотреть пароли в .env
cat .env

# Если нужно сменить пароль:
# 1. Остановить контейнер
./db-manager.sh stop

# 2. Изменить пароль в .env
nano .env

# 3. Удалить контейнер (данные сохранятся)
docker-compose -f docker-compose.prod.yml rm <service>

# 4. Запустить заново
./db-manager.sh start
```

### Проблема: Закончилось место на диске

```bash
# Проверить место
df -h

# Удалить старые бэкапы
find backups/ -type f -mtime +30 -delete

# Очистить Docker
docker system prune -a -f

# Проверить размер данных БД
du -sh arango-data/ postgres-data/ mssql-data/
```

---

## 📊 Рекомендуемые режимы работы

### Режим 1: Ежедневная работа (экономный)
```bash
./db-manager.sh start
```
- ArangoDB + PostgreSQL
- ~1 GB RAM
- Свободно: ~2.8 GB

### Режим 2: Работа с FEMSQ
```bash
./db-manager.sh start        # Базовые БД
./db-manager.sh start-mssql  # Добавить MS SQL

# После работы
./db-manager.sh stop-mssql   # Освободить RAM
```

### Режим 3: Все БД одновременно
```bash
./db-manager.sh start-all
```
- Все три БД
- ~2.6-3 GB RAM
- Свободно: ~800 MB

---

## 🔒 Безопасность

1. **Пароли:** Используйте сильные уникальные пароли
2. **Порты:** БД доступны только с localhost (127.0.0.1)
3. **.env:** Права 600, не коммитить в git
4. **Firewall:** Порты 8529, 5432, 1433 закрыты для внешнего доступа
5. **Бэкапы:** Регулярно создавайте бэкапы
6. **Обновления:** Регулярно обновляйте Docker образы

---

## 📚 Полезные команды

```bash
# Быстрая справка
./db-manager.sh help

# Статус
./db-manager.sh status

# Логи
./db-manager.sh logs arangodb

# Информация для подключения
./db-manager.sh connections

# Мониторинг
./db-manager.sh monitor

# Бэкап
./db-manager.sh backup all

# Остановить MS SQL
./db-manager.sh stop-mssql
```

---

**Дата создания:** 2025-10-11  
**Автор:** fedoc team  
**Версия:** 1.0.0

