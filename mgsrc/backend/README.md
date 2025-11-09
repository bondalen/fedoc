# multigraph backend

Минимальный каркас Flask-приложения для сервиса multigraph.

## Установка окружения

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Для запуска тестов установите dev-зависимости:

```bash
pip install -r requirements-dev.txt
```

## Запуск разработки

```bash
export FEDOC_DATABASE_URL="postgresql://fedoc:fedoc@localhost:5432/fedoc_mg"
python -m fedoc_multigraph.app
```

Приложение создаётся через фабрику `create_app()` и регистрирует health-endpoint `GET /api/health`.

## Структура пакета

- `fedoc_multigraph/app.py` — фабрика приложения, подключение middleware, ошибок и API.
- `fedoc_multigraph/api/` — регистрация blueprint и модулей REST API.
- `fedoc_multigraph/middleware/` — подключаемые middleware (пока заглушка).
- `fedoc_multigraph/errors/` — обработчики ошибок.
- `fedoc_multigraph/validators/` — заглушка под валидацию запросов.
- `fedoc_multigraph/auth/` — заглушка под декораторы авторизации.
- `fedoc_multigraph/config/` — чтение конфигурации из переменных окружения.
- `tests/` — интеграционные и будущие юнит-тесты.

## Разработка

- Перечень задач: `docs/multigraph/aa-main-docs/bb-tasks.md` (раздел 1.1).
- Детальная диаграмма компонентов: `docs/multigraph/aa-main-docs/dc-components-flask.puml`.
- Реестр модулей/компонентов: `docs/multigraph/aa-main-docs/mc-components.md`.

## Тестирование

Интеграционный сценарий для `/api/blocks` использует живую базу данных AGE. Перед запуском убедитесь, что заданы переменные окружения (минимум `FEDOC_DATABASE_URL`).

```bash
export FEDOC_DATABASE_URL="postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc"
pytest -m integration
```
