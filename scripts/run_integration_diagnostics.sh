#!/usr/bin/env bash
#
# Helper to run integration-test diagnostics locally.
# Executes pytest with verbose output, performs AGE health checks via psql,
# and collects container logs if the docker service is available.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_ROOT="${ARTIFACT_ROOT:-$ROOT_DIR/dev/integration-diagnostics}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
RUN_DIR="$ARTIFACT_ROOT/$TIMESTAMP"
mkdir -p "$RUN_DIR"

DB_URL="${FEDOC_DATABASE_URL:-postgresql://postgres:fedoc_test_2025@127.0.0.1:15432/fedoc}"

if [[ ! -d "venv" ]]; then
  echo "❌ Виртуальное окружение venv не найдено. Выполните 'python3 -m venv venv' и установите зависимости."
  exit 1
fi

source venv/bin/activate

echo "==> Используемое окружение"
echo "Root: ${ROOT_DIR}"
echo "Artifacts: ${RUN_DIR}"
echo "FEDOC_DATABASE_URL: ${DB_URL}"
echo

PYTEST_EXIT=0
echo "==> Запуск pytest -m integration -vv --maxfail=1"
if ! pytest -m integration -vv --maxfail=1 2>&1 | tee "${RUN_DIR}/pytest.log"; then
  PYTEST_EXIT=$?
  echo "⚠️ pytest завершился с кодом ${PYTEST_EXIT}"
fi

echo
echo "==> Проверка AGE через psql"
if command -v psql >/dev/null 2>&1; then
  {
    echo "\set ON_ERROR_STOP on"
    echo "LOAD 'age';"
    echo "SET search_path = ag_catalog, \"\$user\", public;"
    echo "SELECT * FROM cypher('mg_blocks', \$\$MATCH (n) RETURN count(n) AS total$$) AS (count agtype);"
    echo "SELECT * FROM cypher('mg_designs', \$\$MATCH (n) RETURN count(n) AS total$$) AS (count agtype);"
  } | psql "${DB_URL}" > "${RUN_DIR}/psql.log" 2>&1 || {
    echo "⚠️ psql возвратил ошибку, детали в ${RUN_DIR}/psql.log"
  }
else
  echo "⚠️ psql не найден в PATH; пропускаем проверку."
fi

echo
echo "==> Сбор логов контейнера fedoc-multigraph"
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^fedoc-multigraph$'; then
  if ! docker logs fedoc-multigraph > "${RUN_DIR}/docker-fedoc-multigraph.log" 2>&1; then
    echo "⚠️ Не удалось получить логи контейнера; см. ${RUN_DIR}/docker-fedoc-multigraph.log"
  fi
else
  echo "ℹ️ Контейнер fedoc-multigraph не найден или недоступен — шаг пропущен."
fi

echo
echo "==> Сводка"
echo "Pytest exit code: ${PYTEST_EXIT}"
echo "Артефакты сохранены в ${RUN_DIR}"

exit ${PYTEST_EXIT}

