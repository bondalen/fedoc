# fedoc - FEMSQ Documentation System

Централизованная система правил и проектной документации для группы проектов.

**Статус:** 🚧 Проект в стадии проектирования  
**Создан:** 2025-01-28  
**Автор:** Александр

---

## 🎯 О проекте

**fedoc** - это система для управления проектной документацией, которая:

- 📦 Хранит общие "строительные блоки" документации
- ♻️ Позволяет переиспользовать решения между проектами
- 🧠 Накапливает знания без повторной адаптации
- 📋 Управляет правилами и шаблонами

### Откуда появился fedoc

Проект создан на основе системы документации из [FEMSQ](https://github.com/bondalen/femsq) - системы работы с контрагентами при капитальном строительстве, где была разработана проработанная система JSON-документации с DAG-структурой задач.

---

## 🏗️ Архитектура

- **База данных:** ArangoDB Community Edition (Multi-Model)
- **Язык:** Python 3.10+
- **Интеграция:** MCP Server для Cursor AI
- **Развертывание:** Docker Compose
- **Лицензия:** Apache 2.0

### Технологический стек

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| База данных | ArangoDB | Document + Graph + Key-Value |
| Скрипты | Python 3.10+ | Миграция, извлечение, запросы |
| Драйвер БД | python-arango | Работа с ArangoDB |
| Cursor интеграция | MCP Server | Прямой доступ из IDE |
| Контейнеризация | Docker Compose | Изоляция и переносимость |

---

## 📁 Структура проекта

```
fedoc/
├── src/                       # Исходный код
│   ├── mcp_server/           # MCP-сервер для Cursor AI
│   │   ├── handlers/         # Обработчики команд
│   │   └── server.py         # Главный файл сервера
│   └── lib/                  # Переиспользуемые библиотеки
│       └── graph_viewer/     # Визуализация графов ArangoDB
├── dev/                       # Инструменты разработки
│   ├── docker/               # Docker-конфигурации БД
│   └── tools/                # CLI утилиты (view-graph.sh)
├── docs/                      # Актуальная документация
│   ├── project/              # Проектная документация
│   │   ├── project-docs.json # Архитектура проекта
│   │   └── decisions/        # ADR документы
│   ├── development/          # Планирование (в процессе)
│   └── journal/              # Журнал разработки (в процессе)
├── docs-preliminary/         # Предварительная документация
│   ├── examples/             # Примеры (FEMSQ)
│   ├── visualizations/       # Схемы и диаграммы
│   └── project-history/      # История разработки (чаты)
└── requirements.txt          # Python зависимости
```

---

## 🔧 Компоненты

### MCP Server
Сервер Model Context Protocol для интеграции с Cursor AI.

- **Расположение:** `src/mcp_server/`
- **Команды:** `show_graph`, `query_graph`, `get_rules`
- **Документация:** [MCP README](src/mcp_server/README.md), [ADR-002](docs/project/decisions/002-mcp-integration.md)

### Graph Viewer
Библиотека для визуализации графов проектов из ArangoDB.

- **Расположение:** `src/lib/graph_viewer/`
- **Использование:** через MCP или CLI (`dev/tools/view-graph.sh`)
- **Документация:** [Graph Viewer README](src/lib/graph_viewer/README.md), [ADR-003](docs/project/decisions/003-graph-viewer-arch.md)

---

## 📚 Документация

### Проектная документация
- [Архитектура проекта](docs/project/project-docs.json) - структурированное описание
- [Архитектурные решения (ADR)](docs/project/decisions/) - важные технические решения
  - [001: Выбор ArangoDB](docs/project/decisions/001-arangodb-choice.md)
  - [002: Интеграция через MCP](docs/project/decisions/002-mcp-integration.md)
  - [003: Архитектура Graph Viewer](docs/project/decisions/003-graph-viewer-arch.md)

### Инструкции
- [Установка и использование](docs-preliminary/INSTALLATION.md) - полное руководство
- [Визуализация графов](docs-preliminary/visualizations/README.md) - работа с graph viewer

### Концепции и примеры
- [Концепция централизованной системы](docs-preliminary/concepts/centralized-documentation-system-concept.md)
- [FEMSQ - эталонный пример](docs-preliminary/examples/femsq/README.md)
- [История создания проекта](docs-preliminary/project-history/)

---

## 🧱 Основные концепции

### 4 уровня абстракции

1. **Meta-паттерны** - универсальные паттерны
   - displayName, attributes, artifact, links

2. **Структурные блоки** - переиспользуемые элементы
   - Module, Component, Class, Task-DAG, Tree, Chat/Log

3. **Системные правила** - общие для всех проектов
   - Нумерация 01-zz, ссылки type:path, статусы с эмодзи

4. **Доменные расширения** - технологические специфики
   - Maven, Spring Boot, MS SQL Server, Vue.js

### Пример: DAG-структура задач из FEMSQ

```
Задача 0004 присутствует в 3 деревьях:
(Task:0004) -[IN_TREE]-> (Tree:01)  # Дерево артефактов: 01.01.01.01
(Task:0004) -[IN_TREE]-> (Tree:02)  # Дерево функционала: 02.01.01
(Task:0004) -[IN_TREE]-> (Tree:0a)  # Дерево модулей: 0a.01.01
```

---

## 🚀 Быстрый старт

### Установка

Подробная инструкция в [INSTALLATION.md](docs-preliminary/INSTALLATION.md).

**Кратко:**

```bash
# 1. Клонировать репозиторий
git clone https://github.com/bondalen/fedoc.git
cd fedoc

# 2. Установить зависимости Python
pip install -r requirements.txt

# 3. Запустить визуализацию графа (требуется ArangoDB)
dev/tools/view-graph.sh
```

### Развертывание баз данных на сервере

```bash
# Автоматическое развертывание (рекомендуется)
cd dev/docker
chmod +x deploy-to-server.sh
./deploy-to-server.sh
```

**Развертываются (все БД по требованию):**
- 🗄️ ArangoDB 3.11 (Multi-Model БД для fedoc) - ~600 MB RAM
- 🗄️ PostgreSQL 16 (универсальная реляционная БД) - ~400 MB RAM
- 🗄️ MS SQL Server 2022 (для FEMSQ и др.) - ~1.8 GB RAM

**Запуск по требованию:** максимальная гибкость и экономия ресурсов!

**Документация:**
- [Быстрый старт](dev/docker/QUICKSTART.md)
- [Полная инструкция](dev/docker/DEPLOYMENT.md)
- [Рекомендации по развертыванию](docs-preliminary/deployment-recommendations.md)

---

## 🚀 Планы развития

### Фаза 1: Инфраструктура ✅
- ✅ Создание структуры проекта
- ✅ Копирование документации FEMSQ как образца
- ✅ Docker конфигурация (ArangoDB + PostgreSQL + MS SQL)
- ✅ Скрипты управления БД
- ✅ Базовые Python скрипты
- ✅ Библиотека визуализации графов (graph_viewer)

### Фаза 2: Миграция
- ⏳ Скрипты миграции JSON → ArangoDB
- ⏳ Миграция FEMSQ как тестовый пример
- ⏳ Валидация данных

### Фаза 3: Извлечение блоков
- ⏳ Анализаторы паттернов
- ⏳ Генераторы шаблонов
- ⏳ Извлечение блоков из FEMSQ

### Фаза 4: Интеграция с Cursor (в процессе) 🔄
- ✅ Базовая структура MCP Server
- ✅ Интеграция graph_viewer через MCP
- ⏳ Команды для работы с правилами
- ⏳ Команды для работы с проектами
- ⏳ Тестирование работы из Cursor AI

### Фаза 5: Тестирование
- ⏳ Создание нового проекта из шаблонов FEMSQ
- ⏳ Оценка эффективности

---

## 🔗 Связанные проекты

- **[FEMSQ](https://github.com/bondalen/femsq)** - эталонный пример документации
- **[fedoc](https://github.com/bondalen/fedoc)** - этот проект

---

## 📄 Лицензия

Apache License 2.0

---

**Репозиторий:** https://github.com/bondalen/fedoc  
**Автор:** Александр  
**Создано:** 2025-01-28
