# multigraph backend

Минимальный каркас Flask-приложения для сервиса multigraph.

## Установка окружения

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
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

## Разработка

- Перечень задач: `docs/multigraph/aa-main-docs/bb-tasks.md` (раздел 1.1).
- Детальная диаграмма компонентов: `docs/multigraph/aa-main-docs/dc-components-flask.puml`.
- Реестр модулей/компонентов: `docs/multigraph/aa-main-docs/mc-components.md`.
