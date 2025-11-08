# Тестирование связки shiv + psycopg2-binary (2025-11-08)

**Цель:** убедиться, что упаковка Python-приложения в `.pyz` через `shiv` корректно работает с драйвером `psycopg2-binary` в среде, идентичной рабочему контейнеру базы данных fedoc.

---

## Окружение

- **Сервер:** `fedoc-server` (Ubuntu 22.04.5 LTS)
- **Базовый контейнер:** `apache/age` (используется для `fedoc-postgres-age`)
- **Сеть контейнера:** `--network container:fedoc-postgres-age` (общий namespace с рабочей БД)
- **PostgreSQL:** 16.10 (Apache AGE), учётные данные взяты из переменных окружения контейнера (`POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=fedoc_test_2025`, `POSTGRES_DB=fedoc`)

Контейнер запускался с флагом `--rm`, поэтому после выхода все установленные пакеты и файлы были удалены.

---

## Ход тестов

### 1. Запуск временного контейнера
```bash
docker run --rm \
  --name age-psycopg2-test \
  --network container:fedoc-postgres-age \
  apache/age \
  bash -lc '<команды>'
```

### 2. Подготовка окружения внутри контейнера
- `apt-get update`
- Установка пакетов: `python3`, `python3-pip`, `python3-venv`, `gcc`, `libpq-dev`
- Создание виртуального окружения `/tmp/venv`
- Обновление `pip`
- Установка зависимостей: `shiv`, `psycopg2-binary`

### 3. Создание минимального пакета
```text
/tmp/testpkg/
├── setup.py          # setuptools конфигурация
└── test_app.py       # скрипт с SELECT 1 через psycopg2
```

`test_app.py` выполняет подключение к `localhost:5432`, выполняет `SELECT 1` и выводит результат.

### 4. Сборка `.pyz`
```bash
/tmp/venv/bin/shiv \
  --site-packages "$(/tmp/venv/bin/python -c 'import site; print(site.getsitepackages()[0])')" \
  /tmp/testpkg \
  --python "/usr/bin/env python3" \
  --compressed \
  --output-file /tmp/test_app.pyz \
  --entry-point test_app:main
```

### 5. Запуск итогового артефакта
```bash
python3 /tmp/test_app.pyz
# Вывод: result: (1,)
```

Результат подтверждает, что `psycopg2-binary` корректно работает внутри `.pyz` и успешно подключается к рабочей БД.

---

## Выводы

- Связка `shiv + psycopg2-binary` полностью работоспособна в среде контейнера `apache/age`.
- Дополнительных системных библиотек (помимо `libpq-dev` и стандартных build-инструментов) не потребуется.
- Выбор архитектуры с единым `.pyz` артефактом подтверждён практикой; можно переходить к реализации backend с уверенностью, что упаковка и развёртывание будут работать.

---

**Дата тестирования:** 2025-11-08  
**Исполнители:** Александр, Claude (Cursor AI)
