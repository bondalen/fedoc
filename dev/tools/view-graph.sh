#!/bin/bash
# Обёртка для запуска graph_viewer из командной строки

# Определить корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Добавить src в PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Параметры подключения к ArangoDB
ARANGO_PASSWORD="${ARANGO_PASSWORD:-aR@ng0Pr0d2025xK9mN8pL}"

# Запустить viewer
python3 -m lib.graph_viewer.viewer \
    --password "$ARANGO_PASSWORD" \
    "$@"
