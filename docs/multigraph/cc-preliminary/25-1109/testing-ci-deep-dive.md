# Детальный отчёт: Тестирование и CI multigraph

**Дата:** 2025-11-09  
**Статус:** актуально  
**Связанные разделы:** [../aa-main-docs/aa-project.md](../../aa-main-docs/aa-project.md#-Тестирование-и-CI), [../bb-chats/chat-25-1109-resume-12-45.md](../../bb-chats/chat-25-1109-resume-12-45.md), [../bb-chats/chat-25-1109-resume-13-15.md](../../bb-chats/chat-25-1109-resume-13-15.md)

---

## 1. Цель документа

Собрать расширенный контекст по организации тестирования и CI-пайплайна для backend `fedoc_multigraph`: локальный запуск, подготовка демо-данных, интеграционные сценарии, GitHub Actions, а также план по дальнейшему усилению проверок.

---

## 2. Локальное тестирование

### 2.1 Предварительные условия
- **Python:** 3.12 (виртуальное окружение `venv` в корне репозитория).
- **PostgreSQL/AGE:** доступный инстанс (локально через SSH-туннель на порт `15432`).
- **Переменные среды:** `FEDOC_DATABASE_URL=postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc`.

### 2.2 Сидер демо-данных
Команда:
```bash
cd /home/alex/fedoc/mgsrc/backend
python -m fedoc_multigraph.scripts.seed_multigraph --force \
  --dsn "postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc"
```
Что делает скрипт:
1. Очищает графы `mg_blocks`, `mg_designs` и таблицу `mg.design_to_block`.
2. Создаёт базовые блоки: Core Platform, Authentication Module, UI Library.
3. Добавляет дизайны: Project Atlas, Prototype Nova, Docs Template.
4. Формирует проект **Reference Implementation** с ребром `design_edge` между двумя дизайнами.

### 2.3 Запуск интеграционных тестов
```bash
cd /home/alex/fedoc
source venv/bin/activate
pytest -m integration
```
Результат на 2025-11-09: **16 passed**, warnings (Pytest mark registration) планируется устранить в отдельной задаче.

### 2.4 Покрытие сценариев
- `/api/blocks`: CRUD, 404, 422.
- `/api/designs`: CRUD, изменение `block_id`, 404, 409, 422.
- `/api/projects`: CRUD, `design_edge_to_project`, граф (узлы/рёбра/блоки), устойчивость к удалённым рёбрам, конфликты имён, отсутствующие сущности.
- `/api/health`: smoke-check.

---

## 3. GitHub Actions

### 3.1 Workflow `integration-tests.yml`
Триггеры:
- `push` в `main`;
- `pull_request` в `main`.

### 3.2 Шаги пайплайна
1. **Checkout & Python setup**  
   `actions/checkout@v4`, `actions/setup-python@v5 (python-version: 3.12)`.
2. **Установка зависимостей**  
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r mgsrc/backend/requirements.txt
   pip install -r mgsrc/backend/requirements-dev.txt
   ```
3. **PostgreSQL/AGE сервис**  
   - image `apache/age:latest`;  
   - env: `POSTGRES_DB=fedoc`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=fedoc_test_2025`;  
   - проброс порта `5432:5432`;  
   - health-check через `pg_isready`.
4. **Инициализация AGE**  
   Осуществляется серией `psql` запросов:
   - `CREATE EXTENSION IF NOT EXISTS age;`  
   - `LOAD 'age'; SET search_path = ag_catalog, "$user", public;`  
   - `SELECT create_graph('mg_blocks'); SELECT create_vlabel('mg_blocks', 'block_type');`  
   - `SELECT create_graph('mg_designs'); SELECT create_vlabel('mg_designs', 'design_node');`  
   - Создание схемы `mg` и таблицы `mg.design_to_block` с внешними ключами на `mg_blocks.block_type` и `mg_designs.design_node`.
5. **Запуск тестов**  
   ```
   source venv/bin/activate
   cd mgsrc/backend
   export FEDOC_DATABASE_URL="postgresql://postgres:fedoc_test_2025@localhost:5432/fedoc"
   pytest -m integration
   ```

### 3.3 Артефакты и время
- Среднее время выполнения: ~4 мин (подъём контейнера + инициализация AGE).
- Отчёты pytest выводятся в лог workflow; дополнительных артефактов пока не сохраняется.

---

## 4. Диагностика и отладка

### 4.1 Типовые проблемы
- **`ModuleNotFoundError: No module named 'arango'`**  
  Решение: перейти на `psycopg2` + ensure `requirements.txt` установлен.
- **`psycopg2.errors.UndefinedObject: type "agtype" does not exist`**  
  Причина: AGE не загружен или `search_path` не установлен.  
  Решение: `LOAD 'age'; SET search_path = ag_catalog, "$user", public;`.
- **`psycopg2.errors.FeatureNotSupported: SET clause expects a map`**  
  Возникало при использовании параметров в Cypher; решено генерацией map literal в репозиториях.
- **`server closed the connection unexpectedly`**  
  Лейблы `block_type` и `design_node` были созданы с лишними колонками. Пересоздание в чистом виде исправило проблему.

### 4.2 Отладка графовых идентификаторов
- Для сравнения значений используем `id(vertex) = '<value>'::graphid`.
- В тестах при необходимости создаём рёбра через SQL (`INSERT INTO ... design_edge`) c `RETURNING id::text`.

---

## 5. План дальнейшего развития

1. **Маркировка pytest**  
   Зарегистрировать `integration` в `pytest.ini` (`markers = integration: ...`) — устранить предупреждения.
2. **Фикстуры для тестов**  
   Вынести создание блоков/дизайнов/проектов в вспомогательные функции для сокращения кода.
3. **Расширение сидера**  
   Добавить:
   - дополнительные типы рёбер (`depends_on`, `extends`);
   - несколько проектов с разными статусами дизайнов;
   - smoke-данные для будущего `/api/projects/<id>/graph` визуализатора.
4. **Покрытие WebSocket и MCP**  
   После реализации каналов `/ws` и MCP-команд — разработать сценарии в отдельном workflow.
5. **Отчёты о тестах**  
   Рассмотреть публикацию `pytest --junitxml` в GitHub Actions для отслеживания истории.

---

## 6. Ссылки и материалы

- Основной документ проекта: [../../aa-main-docs/aa-project.md](../../aa-main-docs/aa-project.md)
- Реестр компонентов: [../../aa-main-docs/mc-components.md](../../aa-main-docs/mc-components.md)
- Workflow GitHub Actions: [../../../.github/workflows/integration-tests.yml](../../../.github/workflows/integration-tests.yml)
- Код сидера: [../../../mgsrc/backend/fedoc_multigraph/scripts/seed_multigraph.py](../../../mgsrc/backend/fedoc_multigraph/scripts/seed_multigraph.py)
- Интеграционные тесты проектов: [../../../mgsrc/backend/tests/integration/test_projects_api.py](../../../mgsrc/backend/tests/integration/test_projects_api.py)

---

**Ответственный:** Александр  
**Следующее обновление:** после расширения покрытия тестами WebSocket/MCP.

