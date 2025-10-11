# Запуск баз данных по требованию

**Философия:** Все три БД запускаются только когда нужны - максимальная экономия ресурсов и гибкость.

---

## 🎯 Преимущества подхода "по требованию"

### 1. Максимальная экономия ресурсов
- **0 MB RAM** когда БД не используются
- Запускаете только то, что нужно прямо сейчас
- Остановили работу - остановили БД

### 2. Гибкость
- Работаете только с fedoc → только ArangoDB (~600 MB)
- Работаете с другим проектом → только PostgreSQL (~400 MB)
- Работаете с FEMSQ → добавляете MS SQL (~1.5 GB)

### 3. Контроль
- Полный контроль над запуском каждой БД
- Легко экспериментировать и тестировать
- Нет "зависших" процессов

---

## 📊 Сценарии использования

### Сценарий 1: Работа только с fedoc
**Задача:** Разработка системы документации fedoc

```bash
# Утро - начало работы
./db-manager.sh start-arango

# Работа...
# - Создание схемы БД
# - Миграция FEMSQ
# - Извлечение паттернов

# Вечер - завершение работы
./db-manager.sh stop-arango
```

**Потребление:** ~600 MB RAM  
**Свободно:** ~3.2 GB

---

### Сценарий 2: Разработка нового проекта на PostgreSQL
**Задача:** Создание REST API на Django/FastAPI

```bash
# Запустить PostgreSQL
./db-manager.sh start-postgres

# Работа...
# - Создание моделей
# - Миграции Django
# - Тестирование API

# Остановить после работы
./db-manager.sh stop-postgres
```

**Потребление:** ~400 MB RAM  
**Свободно:** ~3.4 GB

---

### Сценарий 3: Работа с FEMSQ
**Задача:** Разработка функционала в FEMSQ (требует MS SQL)

```bash
# Запустить MS SQL
./db-manager.sh start-mssql

# Работа с FEMSQ...
# - Backend на Spring Boot
# - Frontend на Vue.js
# - GraphQL API

# Остановить после работы (освободить ~1.5 GB!)
./db-manager.sh stop-mssql
```

**Потребление:** ~1.8 GB RAM  
**Свободно:** ~2 GB

---

### Сценарий 4: Параллельная работа над fedoc и другим проектом
**Задача:** Одновременная работа с fedoc и PostgreSQL проектом

```bash
# Запустить базовые БД
./db-manager.sh start

# Работа...
# - fedoc в ArangoDB
# - Другой проект в PostgreSQL

# Остановить всё
./db-manager.sh stop
```

**Потребление:** ~1 GB RAM  
**Свободно:** ~2.8 GB

---

### Сценарий 5: Миграция данных между БД
**Задача:** Перенос данных из PostgreSQL в ArangoDB

```bash
# Запустить обе БД
./db-manager.sh start-arango
./db-manager.sh start-postgres

# Миграция...

# Остановить то, что больше не нужно
./db-manager.sh stop-postgres
```

---

### Сценарий 6: Полное тестирование всех проектов
**Задача:** Интеграционное тестирование всех систем

```bash
# Запустить все БД
./db-manager.sh start-all

# Тестирование...

# Остановить всё
./db-manager.sh stop
```

**Потребление:** ~2.8 GB RAM  
**Свободно:** ~1 GB

---

## ⚡ Быстрые команды

### Запуск отдельных БД
```bash
./db-manager.sh start-arango     # ArangoDB: ~600 MB
./db-manager.sh start-postgres   # PostgreSQL: ~400 MB
./db-manager.sh start-mssql      # MS SQL: ~1.8 GB
```

### Комбинации
```bash
./db-manager.sh start            # ArangoDB + PostgreSQL: ~1 GB
./db-manager.sh start-all        # Все три: ~2.8 GB
```

### Остановка
```bash
./db-manager.sh stop-arango      # Остановить ArangoDB
./db-manager.sh stop-postgres    # Остановить PostgreSQL
./db-manager.sh stop-mssql       # Остановить MS SQL
./db-manager.sh stop             # Остановить всё
```

### Проверка
```bash
./db-manager.sh status           # Что запущено?
./db-manager.sh monitor          # Реальное время
```

---

## 📈 Таблица потребления ресурсов

| Конфигурация | RAM | Свободно | Когда использовать |
|--------------|-----|----------|-------------------|
| Ничего не запущено | 0 MB | 3.8 GB | Сервер в простое |
| Только ArangoDB | 600 MB | 3.2 GB | Работа с fedoc |
| Только PostgreSQL | 400 MB | 3.4 GB | Работа с PG проектами |
| Только MS SQL | 1.8 GB | 2.0 GB | Работа с FEMSQ |
| Arango + PostgreSQL | 1.0 GB | 2.8 GB | Параллельная работа |
| Arango + MS SQL | 2.4 GB | 1.4 GB | fedoc + FEMSQ |
| PostgreSQL + MS SQL | 2.2 GB | 1.6 GB | Редко |
| Все три БД | 2.8 GB | 1.0 GB | Полное тестирование |

---

## 💡 Советы и best practices

### 1. Запускайте минимум
```bash
# Плохо (если не нужны все БД)
./db-manager.sh start-all

# Хорошо (только то, что нужно)
./db-manager.sh start-arango
```

### 2. Останавливайте после работы
```bash
# В конце рабочего дня
./db-manager.sh stop
```

### 3. Мониторьте ресурсы
```bash
# Проверить потребление
./db-manager.sh status

# Посмотреть в реальном времени
./db-manager.sh monitor
```

### 4. Используйте алиасы
```bash
# Добавить в ~/.bashrc
alias db-start='cd /home/user1/fedoc/docker && ./db-manager.sh start'
alias db-stop='cd /home/user1/fedoc/docker && ./db-manager.sh stop'
alias db-status='cd /home/user1/fedoc/docker && ./db-manager.sh status'
```

### 5. Автоматизируйте рутину
```bash
# Скрипт начала рабочего дня
#!/bin/bash
cd /home/user1/fedoc/docker
./db-manager.sh start
echo "БД запущены, можно работать!"
```

---

## 🎓 Часто задаваемые вопросы

### Q: Нужно ли держать БД запущенными постоянно?
**A:** Нет! Это и есть суть подхода "по требованию". Запускаете когда нужно, останавливаете после работы.

### Q: Что произойдет с данными при остановке?
**A:** Ничего! Данные хранятся в Docker volumes и полностью сохраняются.

### Q: Можно ли запустить БД автоматически при загрузке сервера?
**A:** Да, но это противоречит подходу "по требованию". Если нужен автозапуск, измените `restart: "no"` на `restart: unless-stopped` в docker-compose.prod.yml.

### Q: Сколько времени занимает запуск БД?
**A:** 
- ArangoDB: ~10-15 секунд
- PostgreSQL: ~5-10 секунд
- MS SQL: ~30-40 секунд

### Q: Как проверить, что БД запустилась успешно?
**A:** `./db-manager.sh status` покажет статус всех контейнеров.

---

## 🔧 Troubleshooting

### Проблема: БД не запускается
```bash
# Проверить логи
./db-manager.sh logs <service>

# Проверить порты
sudo netstat -tulpn | grep -E '8529|5432|1433'
```

### Проблема: Нехватка памяти
```bash
# Проверить потребление
free -h

# Остановить ненужные БД
./db-manager.sh stop-mssql  # Освободит ~1.5 GB
```

### Проблема: Забыл что запущено
```bash
# Статус
./db-manager.sh status

# Или через Docker
docker ps
```

---

## 📚 См. также

- [DEPLOYMENT.md](DEPLOYMENT.md) - Полная инструкция
- [README.md](README.md) - Обзор Docker конфигурации
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт

---

**Философия:** Запускайте только то, что нужно, когда нужно. Экономьте ресурсы и сохраняйте контроль!

