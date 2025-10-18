# Сборка образа PostgreSQL + Apache AGE

## Обоснование

Официальный образ `postgres:16-alpine` НЕ включает расширение Apache AGE.
Нужно собрать собственный образ с установленным AGE.

## Образ

**Dockerfile:** `Dockerfile.postgres-age`  
**Базовый образ:** `postgres:16-alpine`  
**Добавлено:** Apache AGE 1.6.0 (ветка PG16/v1.6.0)

## Сборка образа

### На сервере (рекомендуется)

```bash
# Подключиться к серверу
ssh vuege-server

# Перейти в директорию
cd ~/fedoc/dev/docker

# Собрать образ
docker build -f Dockerfile.postgres-age -t fedoc/postgres-age:16-1.6.0 .

# Проверить образ
docker images | grep postgres-age
```

**Время сборки:** ~3-5 минут  
**Размер образа:** ~250-300 MB

### Локально (опционально)

```bash
cd /home/alex/fedoc/dev/docker
docker build -f Dockerfile.postgres-age -t fedoc/postgres-age:16-1.6.0 .
```

## Запуск контейнера

После сборки образа:

```bash
# Остановить и удалить старый контейнер
./db-manager.sh stop-postgres
docker rm fedoc-postgres
sudo rm -rf postgres-data/*

# Запустить с новым образом (docker-compose автоматически использует собранный образ)
./db-manager.sh start-postgres
```

## Проверка AGE

```bash
# Подключиться к PostgreSQL
docker exec -it fedoc-postgres psql -U postgres -d fedoc

# В psql:
SELECT extname, extversion FROM pg_extension WHERE extname = 'age';
```

**Ожидаемый результат:**
```
 extname | extversion 
---------+------------
 age     | 1.6.0
(1 row)
```

## Обновление образа

При обновлении версии AGE:

1. Изменить ветку в Dockerfile: `--branch PG16/v1.6.1`
2. Изменить тег образа: `fedoc/postgres-age:16-1.6.1`
3. Пересобрать: `docker build ...`
4. Обновить docker-compose.prod.yml

## Альтернативы

### Вариант 1: Использовать готовый образ Apache AGE

```yaml
postgres:
  image: apache/age:PG16_latest
  # Но может отличаться от стандартного postgres образа
```

**Минус:** Меньше контроля над конфигурацией

### Вариант 2: Установка AGE в runtime

Установить AGE при каждом запуске контейнера (медленно).

**Минус:** Увеличивает время старта на 3-5 минут

## Troubleshooting

### Ошибка "extension age is not available"

**Причина:** Образ без AGE  
**Решение:** Собрать образ с помощью этого Dockerfile

### Ошибка при сборке "make: command not found"

**Причина:** Не установлены зависимости сборки  
**Решение:** Проверить что apk add выполнился успешно

### Большой размер образа

**Решение:** Убедиться что build-deps удалились (`apk del .build-deps`)

---

**Дата создания:** 18 октября 2025  
**Автор:** Александр

