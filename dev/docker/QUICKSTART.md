# Быстрое развертывание на сервере 176.108.244.252

## 🚀 Автоматическое развертывание (рекомендуется)

Запустите на своей локальной машине:

```bash
cd /home/alex/fedoc/docker
chmod +x deploy-to-server.sh
./deploy-to-server.sh
```

Скрипт автоматически:
1. ✅ Проверит доступ к серверу
2. ✅ Удалит старые Docker образы (openjdk)
3. ✅ Клонирует/обновит репозиторий fedoc
4. ✅ Создаст .env с безопасными паролями
5. ✅ Загрузит Docker образы БД
6. ✅ Запустит ArangoDB и PostgreSQL
7. ✅ Проверит работоспособность

**Время:** ~5-10 минут

---

## 📋 Ручное развертывание

### Шаг 1: Подключиться к серверу
```bash
ssh user1@176.108.244.252
```

### Шаг 2: Очистить старые образы
```bash
docker rmi openjdk:21-slim
docker system prune -f
```

### Шаг 3: Клонировать репозиторий
```bash
cd /home/user1
git clone https://github.com/bondalen/fedoc.git
cd fedoc/docker
chmod +x db-manager.sh
```

### Шаг 4: Настроить пароли
```bash
cp .env.example .env
nano .env  # Установить надежные пароли
chmod 600 .env
```

### Шаг 5: Запустить нужные БД (по требованию)
```bash
# Вариант 1: Только ArangoDB для fedoc
./db-manager.sh start-arango

# Вариант 2: ArangoDB + PostgreSQL (рекомендуется)
./db-manager.sh start

# Вариант 3: Все БД сразу
./db-manager.sh start-all
```

### Шаг 6: Проверить
```bash
./db-manager.sh status
```

**Время:** ~10-15 минут

---

## 🔧 После установки

### Проверить статус
```bash
ssh user1@176.108.244.252
cd /home/user1/fedoc/docker
./db-manager.sh status
```

### Доступ к Web UI ArangoDB
```bash
# На локальной машине
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N

# В браузере: http://localhost:8529
# User: root
# Password: (из .env на сервере)
```

### Создать бэкап
```bash
./db-manager.sh backup all
```

---

## 📚 Дополнительно

- **Полная документация:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Справка по командам:** `./db-manager.sh help`
- **README:** [README.md](README.md)

---

## ⚡ Быстрые команды

```bash
# Статус
./db-manager.sh status

# Запуск по требованию
./db-manager.sh start-arango     # Только ArangoDB
./db-manager.sh start-postgres   # Только PostgreSQL
./db-manager.sh start-mssql      # Только MS SQL
./db-manager.sh start            # ArangoDB + PostgreSQL
./db-manager.sh start-all        # Все БД

# Остановка
./db-manager.sh stop-arango      # Остановить ArangoDB
./db-manager.sh stop-mssql       # Остановить MS SQL
./db-manager.sh stop             # Остановить всё

# Логи
./db-manager.sh logs arangodb

# Мониторинг
./db-manager.sh monitor

# Бэкап
./db-manager.sh backup all

# Справка
./db-manager.sh help
```

