# fedoc MCP Server

MCP-сервер для интеграции проекта fedoc с Cursor AI.

## 🎯 Назначение

Предоставляет доступ к функциональности fedoc через Model Context Protocol (MCP):
- Визуализация графов проектов
- Запросы к документации
- Управление правилами
- Работа с проектами

## 🚀 Установка

```bash
cd src/mcp_server
pip install -r requirements.txt
```

## ⚙️ Конфигурация

Добавьте в `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "fedoc": {
      "command": "python",
      "args": ["/home/alex/projects/rules/fedoc/src/mcp_server/server.py"],
      "env": {
        "ARANGO_HOST": "http://localhost:8529",
        "ARANGO_DB": "fedoc",
        "ARANGO_USER": "root",
        "ARANGO_PASSWORD": "aR@ng0Pr0d2025xK9mN8pL"
      },
      "description": "fedoc MCP - управление проектной документацией"
    }
  }
}
```

## 📋 Команды

### show_graph
Визуализировать граф проекта в браузере

**Параметры:**
- `project` (str, optional): Фильтр по проекту (fepro, femsq, fedoc)
- `start_node` (str): Стартовая вершина (default: canonical_nodes/c:backend)
- `depth` (int): Глубина обхода (default: 5)
- `theme` (str): Тема (dark/light, default: dark)

**Пример использования в Cursor AI:**
```
Покажи граф проекта FEPRO
```

### query_graph (в разработке)
Выполнить AQL запрос к графу

### get_project_docs (в разработке)
Получить документацию проекта

### list_projects (в разработке)
Список всех проектов

### get_rules (в разработке)
Получить правила для артефакта

## 🔧 Разработка

**Статус:** 🚧 В разработке

Базовая структура создана. Полная реализация MCP протокола в процессе разработки.

**Текущая функциональность:**
- ✅ Базовая структура сервера
- ✅ Интеграция с graph_viewer
- ✅ Обработчик show_graph
- ⏳ Полный MCP протокол
- ⏳ Остальные обработчики

## 📚 Документация

См. также:
- [Библиотека graph_viewer](../lib/graph_viewer/README.md)
- [Проектная документация](../../docs/project/project-docs.json)
- [Архитектурные решения](../../docs/project/decisions/)
