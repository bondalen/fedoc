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
1. Очищает графы `mg_blocks`, `mg_designs`, таблицы `mg.design_to_block`, `mg.design_edge_to_project`, `mg.projects`.
2. Создаёт **7** блоков (Core Platform, Authentication Module, UI Library, Data Warehouse, Analytics Engine, Reporting Service, Notification Service) с различными типами связей `contains`, `depends_on`, `extends`.
3. Добавляет **7** дизайнов (Project Atlas, Prototype Nova, Docs Template, Customer Portal, Security Dashboard, Data Insights Workspace, Mobile Companion) и связывает их с блоками.
4. Формирует **5** рёбер `design_edge` с типами `depends_on`, `extends`, `observes`, `references`.
5. Создаёт **4** проекта (Reference Implementation, Customer Rollout, Analytics Enablement, Mobile Pilot), присваивая каждый набор соответствующих рёбер.

### 2.3 Запуск интеграционных тестов
```bash
cd /home/alex/fedoc
source venv/bin/activate
pytest -m integration
```
Результат на 2025-11-09: **16 passed**.

### 2.4 Покрытие сценариев
- `/api/blocks`: CRUD, 404, 422.
- `/api/designs`: CRUD, изменение `block_id`, 404, 409, 422.
- `/api/projects`: CRUD, `design_edge_to_project`, граф (узлы/рёбра/блоки), устойчивость к удалённым рёбрам, конфликты имён, отсутствующие сущности.
- `/api/health`: smoke-check.

### 2.5 Конфигурация pytest и вспомогательные утилиты (2025-11-09, вторая половина дня)
- Создан корневой `pytest.ini`, поэтому при запуске из корня репозитория автоматически подхватываются `markers = integration`.
- Дублирующий `mgsrc/backend/pytest.ini` удалён.
- В `tests/integration/utils.py` вынесены функции `create_block`, `create_design`, `create_project` и соответствующие `delete_*`, уменьшая дублирование кода в тестах.
- Обновлены сценарии для дизайнов и проектов; все проверки проходят (`16 passed`).

### 2.6 Pre-PR чек-лист для интеграционных тестов
Перед созданием Pull Request выполняем:
1. **Синхронизация зависимостей**  
   ```bash
   source venv/bin/activate
   pip install -r mgsrc/backend/requirements.txt
   pip install -r mgsrc/backend/requirements-dev.txt
   ```
2. **Подготовка БД**  
   ```bash
   ssh -f -N -L 15432:localhost:5432 fedoc-server  # при необходимости
   python -m fedoc_multigraph.scripts.seed_multigraph --force \
     --dsn "postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc"
   ```
3. **Запуск тестов**  
   ```bash
   pytest -m integration
   ```
4. **Проверка статуса**  
   - Убедиться, что `16 passed` без предупреждений.
   - Зафиксировать результаты в описании PR (указать дату, commit SHA и команду).
   - Убедиться, что GitHub Actions workflow `Integration Tests` завершился успешно.
5. **Документация**  
   - Обновить релевантные разделы (`testing-ci-deep-dive.md`, `ab-project-backend.md`, если добавлены новые шаги).

### 2.7 Анализ логов при падении тестов
Если интеграционные тесты падают:
1. **Получить сообщение об ошибке**
   ```bash
   pytest -m integration -vv --maxfail=1
   ```
2. **Проверить состояние AGE**
   ```bash
   psql "postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc" \
     -c "LOAD 'age'; SET search_path = ag_catalog, \"$user\", public; SELECT * FROM cypher('mg_blocks', $$MATCH (n) RETURN count(n)$$) AS (count agtype);"
   ```
3. **Просмотреть логи PostgreSQL/AGE**
   ```bash
   docker exec fedoc-multigraph tail -n 100 /var/log/supervisor/postgres.log
   ```
4. **Проверить логи приложения**
   ```bash
   docker exec fedoc-multigraph tail -n 200 /var/log/supervisor/pythonapp.log
   ```
5. **Повторить сидирование**
   Если проблема в неконсистентных данных, перезапустить сидер и повторить тесты.

### 2.8 Автоматизация диагностики
- Скрипт `scripts/run_integration_diagnostics.sh` выполняет пункты 2.7 последовательно: запускает `pytest -vv`, делает cypher-проверку через `psql`, выгружает логи контейнера `fedoc-multigraph` и сохраняет результаты в `dev/integration-diagnostics/`.
- Запускаем из корня репозитория:
  ```bash
  bash scripts/run_integration_diagnostics.sh
  ```
  При необходимости можно передать переменную `FEDOC_DATABASE_URL`; по умолчанию используется `postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc`.

---

## 3. GitHub Actions

### 3.1 Workflow `integration-tests.yml`
Триггеры:
- `push` в `main`;
- `pull_request` в `main`.

### 3.2 Шаги пайплайна
1. **Checkout & Python setup**  
   `actions/checkout@v4`, `actions/setup-python@v5 (python-version: 3.12)`.
2. **Зависимости**  
   - `sudo apt-get install postgresql-client` для `psql`;
   - создание `venv`, установка `requirements.txt` и `requirements-dev.txt`.
3. **PostgreSQL/AGE сервис**  
   - image `apache/age:latest`, переменные `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`;  
   - health-check через `pg_isready`.
4. **Инициализация AGE**  
   - `CREATE EXTENSION age`, загрузка `LOAD 'age'; SET search_path ...`;  
   - создание графов `mg_blocks`, `mg_designs`, ярлыков `block_type`, `design_node`, `block_edge`, `design_edge`;  
   - создание схемы `mg` + таблиц `projects`, `design_to_block`, `design_edge_to_project` и индексов.
5. **Сидер**  
   - `python -m fedoc_multigraph.scripts.seed_multigraph --force --dsn ${FEDOC_DATABASE_URL}`.
6. **Запуск тестов**  
   - `pytest -m integration --maxfail=1 --junitxml=../reports/integration-junit.xml`.
7. **Артефакты**  
   - логи сервиса (`docker logs postgres`) и `reports/integration-junit.xml` загружаются артефактами.

### 3.3 Артефакты и время
- Среднее время выполнения: ~6–7 минут (холодный старт контейнера + сидирование).
- Логи PostgreSQL и `integration-junit.xml` публикуются артефактами (`integration-test-artifacts`).

### 3.4 SLA и контроль
- **Триггер:** каждый PR/commit, затрагивающий backend `mgsrc/backend/**` или сам workflow.
- **Допустимое время:** не более 10 минут; превышение сигнализирует о проблемах с сидированием или сетью.
- **Артефакты:** обязательные (`integration-junit.xml`, `postgres.log`); скачиваем при падении пайплайна.
- **Принятие PR:** без зелёного статуса workflow PR не сливается (check обязательный).

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

