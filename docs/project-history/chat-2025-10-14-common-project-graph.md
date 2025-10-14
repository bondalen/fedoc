# Отчёт о работе: Создание общего графа проектов

**Дата:** 2025-10-14  
**Чат:** Common Project Graph (создание общего графа проектов)  
**Участники:** Александр, Claude (Cursor AI)  
**Статус:** ✅ Завершено

---

## 📋 Контекст начала работы

### Исходная ситуация

После развёртывания инфраструктуры fedoc и создания схемы БД требовалось построить "общий граф проектов" в ArangoDB для:
- Хранения знаний о технологиях и архитектуре проектов
- Сбора правил для AI-ассистента при работе с артефактами
- Отражения связей между проектами через общие элементы графа

### Цели

1. Построить граф с вершиной "проекты" и узлом "объекты разработки"
2. Раскрыть структуру объектов разработки для fepro, femsq и fedoc
3. Отразить в рёбрах списки проектов, использующих связь
4. Поддержать DAG структуру для множественных путей подъёма при сборе правил

---

## 💬 Ход работы

### Этап 1: Проверка доступности ArangoDB

**Выполнено:**
- ✅ Проверено SSH подключение к серверу 176.108.244.252
- ✅ Проверен статус контейнера ArangoDB
- ✅ Создан SSH туннель для доступа к API
- ✅ Установлен python-arango драйвер

**Результат:**
- ArangoDB 3.11.14 работает корректно
- API доступен через http://localhost:8529
- База данных `fedoc` готова к работе

### Этап 2: Определение структуры графа

**Анализ проектов:**
- **fepro**: full-stack (backend + frontend), PostgreSQL
- **femsq**: full-stack (backend + frontend), MS SQL Server
- **fedoc**: система документации, ArangoDB

**Выявленные пути:**
```
fepro: Объекты разработки → Слой → Бэкенд → БД бэкенда → PostgreSQL
femsq: Объекты разработки → Слой → Бэкенд → БД бэкенда → MS SQL Server
fedoc: Объекты разработки → БД проекта → ArangoDB
```

**Ключевое решение:** Разделить "БД проекта" и "БД бэкенда" на два отдельных узла для чёткости сбора правил.

### Этап 3: Создание базовой структуры

**Созданные коллекции:**
- `projects` - проекты (fepro, femsq, fedoc)
- `canonical_nodes` - канонические узлы графа
- `project_relations` - рёбра графа
- `common_project_graph` - Named Graph

**Базовые узлы:**
- `c:project` - Проект (концептуальный)
- `c:dev-objects` - Объекты разработки
- `c:project-database` - БД проекта
- `c:backend-database` - БД бэкенда

**Принятое решение:**
- Использовать короткие префиксы: `c:` вместо `concept:`, `t:` вместо `tech:`
- Улучшена читаемость графа и диаграмм

### Этап 4: Упрощение структуры рёбер

**Проблема:** Поле `evidence` занимало ~40-50% размера документа

**Решение:** Упрощённая структура ребра
```json
{
  "_from": "canonical_nodes/c:project",
  "_to": "canonical_nodes/c:dev-objects",
  "relationType": "contains",
  "projects": ["fepro", "femsq", "fedoc"],
  "source": "project-documentation",
  "weight": 3,
  "metadata": {"created": "2025-10-14T..."}
}
```

**Результат:** Экономия ~31% места на документ

### Этап 5: Раскрытие структуры бэкенда

**Созданная иерархия зависимостей:**
```
c:backend
└─→ c:backend-stack (технологический стек)
    └─→ t:java@21 (язык программирования)
        └─→ c:backend-framework (фреймворк)
            └─→ t:spring-boot@3.4.5
                ├─→ c:backend-api → t:graphql
                ├─→ c:backend-security
                │   ├─→ c:with-security (fepro) → t:jwt + t:spring-security
                │   └─→ c:no-security (femsq)
                ├─→ c:backend-reactive → t:r2dbc (fepro)
                ├─→ c:backend-cache → t:hazelcast + t:caffeine (fepro)
                ├─→ c:backend-migrations → t:liquibase
                └─→ c:backend-monitoring → t:spring-actuator
```

**Ключевые решения:**
1. Каждый уровень зависит от предыдущего (без предыдущего нет смысла)
2. Безопасность разделена на два варианта: `c:with-security` и `c:no-security`
3. GraphQL зависит от Spring Boot (кто его реализует)
4. Liquibase зависит от Spring Boot (в каком контексте работает)

### Этап 6: Добавление альтернативных стеков

**Для наглядности добавлены:**

**Python/FastAPI стек:**
```
c:backend → c:backend-stack → t:python@3.11 → c:backend-framework → t:fastapi
├─→ c:backend-api → [t:graphql, t:rest]
├─→ c:backend-security → t:jwt
├─→ c:backend-migrations → t:alembic
└─→ c:backend-monitoring → t:prometheus
```

**Node.js/Express стек:**
```
c:backend → c:backend-stack → t:node@18 → c:backend-framework → t:express
├─→ c:backend-api → [t:graphql, t:rest]
└─→ c:backend-security → t:jwt
```

**Распределение проектов:**
- Java/Spring Boot: `projects: ["fepro", "femsq"]`
- Python/FastAPI: `projects: []` (альтернатива)
- Node.js/Express: `projects: []` (альтернатива)

### Этап 7: Восстановление Tom-Select в Graph Viewer

**Проблема:** Утеряна функциональность комбобокса с поиском

**Решение:**
- ✅ Добавлено подключение Tom-Select CSS и JS
- ✅ Заменён обычный `<input list>` на `<select>` с Tom-Select
- ✅ Реализована динамическая загрузка всех узлов
- ✅ Добавлена фильтрация по мере ввода
- ✅ Поддержка поиска по `_key`, `name` и `_id`
- ✅ Обновление списка при смене проекта

**Файлы изменены:**
- `web_viewer.py` - добавлен Tom-Select с динамической загрузкой
- `view-graph.sh` - переключён на динамический сервер

---

## ✅ Выполненные задачи

### Создание узлов графа

**Концептуальные узлы (17):**
- `c:project` - Проект
- `c:dev-objects` - Объекты разработки
- `c:layer` - Слой
- `c:backend` - Бэкенд
- `c:backend-stack` - Стек бэкенда
- `c:backend-framework` - Фреймворк бэкенда
- `c:backend-api` - API бэкенда
- `c:backend-security` - Безопасность бэкенда
- `c:with-security` - С безопасностью
- `c:no-security` - Без безопасности
- `c:backend-reactive` - Реактивность бэкенда
- `c:backend-cache` - Кэш бэкенда
- `c:backend-migrations` - Миграции бэкенда
- `c:backend-monitoring` - Мониторинг бэкенда
- `c:backend-database` - БД бэкенда
- `c:project-database` - БД проекта
- `c:backend-language` - Язык программирования

**Технологические узлы (21):**
- `t:java@21` - Java 21 LTS
- `t:python@3.11` - Python 3.11
- `t:node@18` - Node.js 18
- `t:spring-boot@3.4.5` - Spring Boot 3.4.5
- `t:fastapi` - FastAPI
- `t:express` - Express
- `t:graphql` - GraphQL
- `t:rest` - REST
- `t:jwt` - JWT
- `t:spring-security` - Spring Security
- `t:no-auth` - Без аутентификации
- `t:r2dbc` - R2DBC
- `t:hazelcast` - Hazelcast
- `t:caffeine` - Caffeine
- `t:liquibase` - Liquibase
- `t:alembic` - Alembic
- `t:spring-actuator` - Spring Boot Actuator
- `t:prometheus` - Prometheus
- `t:postgresql@16` - PostgreSQL 16
- `t:mssql@2022` - MS SQL Server 2022
- `t:arangodb@3.11` - ArangoDB 3.11.14

**Всего: 38 узлов**

### Создание рёбер графа

**Рёбра с реальными проектами: 47**
- FEPRO: 42 рёбра (полный стек с безопасностью, кэшем, реактивностью)
- FEMSQ: 27 рёбер (упрощённый стек без безопасности)

**Рёбра альтернативных стеков: 15**
- Python/FastAPI: 10 рёбер
- Node.js/Express: 5 рёбер

**Всего: 62 рёбра**

### Типы связей

- `contains` - иерархическое вложение (30 рёбер)
- `implementedBy` - реализация технологией (20 рёбер)
- `uses` - использование (10 рёбер)
- `variant` - вариант реализации (2 ребра)

### Визуализация графа

**Созданы форматы:**
1. **Graphviz (DOT)** - `common-project-graph.dot`, `*.png`, `*.svg`
2. **Mermaid** - `common-project-graph.mmd`
3. **Текстовые деревья** - `*-fepro.txt`, `*-femsq.txt`
4. **ArangoDB Graph Viewer** с Tom-Select

---

## 📊 Итоговая статистика

### Структура БД

| Коллекция | Тип | Документов | Описание |
|-----------|-----|------------|----------|
| `projects` | Document | 3 | Проекты (fepro, femsq, fedoc) |
| `canonical_nodes` | Document | 38 | Канонические узлы графа |
| `project_relations` | Edge | 62 | Связи между узлами |
| `common_project_graph` | Graph | - | Named Graph |

### Покрытие проектов

| Проект | Рёбер в графе | Особенности |
|--------|---------------|-------------|
| FEPRO | 42 | Полный стек: security + cache + reactive |
| FEMSQ | 27 | Упрощённый стек: без security |
| FEDOC | 8 | Минимальный: только БД |

### Альтернативные стеки (для наглядности)

| Стек | Язык | Фреймворк | Рёбер |
|------|------|-----------|-------|
| Java | t:java@21 | t:spring-boot@3.4.5 | 47 (реальные) |
| Python | t:python@3.11 | t:fastapi | 10 (альтернатива) |
| Node.js | t:node@18 | t:express | 5 (альтернатива) |

---

## 🎯 Результаты

### ✅ Граф проектов создан

- ✅ 38 узлов (17 концептуальных + 21 технологический)
- ✅ 62 рёбра (47 реальных + 15 альтернативных)
- ✅ 3 проекта (fepro, femsq, fedoc)
- ✅ DAG структура поддерживает множественные пути

### ✅ Правильная архитектура зависимостей

- ✅ Язык → Фреймворк → Элементы фреймворка
- ✅ Каждый уровень зависит от предыдущего
- ✅ Безопасность правильно разделена (с/без)
- ✅ Альтернативные стеки для наглядности

### ✅ Упрощённая структура данных

- ✅ Короткие префиксы (`c:`, `t:`) для читаемости
- ✅ Минималистичные узлы (без хранения путей)
- ✅ Минималистичные рёбра (без массива evidence)
- ✅ Экономия ~31% места на документ

### ✅ Инструменты визуализации

- ✅ Graphviz (PNG, SVG) - высокое качество
- ✅ Mermaid - интеграция с Markdown
- ✅ Текстовые деревья - быстрый поиск
- ✅ ArangoDB Graph Viewer с Tom-Select - интерактивность

### ✅ Tom-Select восстановлен

- ✅ Комбобокс с поиском и автодополнением
- ✅ Динамическая загрузка всех узлов из ArangoDB
- ✅ Фильтрация по мере ввода
- ✅ Поиск по `_key`, `name` и `_id`
- ✅ Обновление списка при смене проекта

---

## 💡 Ключевые решения

### Архитектурные

1. **Разделение БД на два узла:**
   - `c:project-database` - БД как основной объект проекта (fedoc)
   - `c:backend-database` - БД как компонент бэкенда (fepro, femsq)
   - **Обоснование:** Чёткое разделение контекстов для сбора правил

2. **Иерархия зависимостей:**
   - Backend → Stack → Language → Framework → Elements
   - **Обоснование:** Отражает реальную архитектуру ("без чего не может быть")

3. **Разделение безопасности:**
   - `c:with-security` (fepro) → JWT + Spring Security
   - `c:no-security` (femsq) - чётко обозначено отсутствие
   - **Обоснование:** Правильная семантика, нет путаницы

4. **Альтернативные стеки:**
   - Python/FastAPI и Node.js/Express с `projects: []`
   - **Обоснование:** Наглядность возможных архитектур, REST как альтернатива GraphQL

### Технические

1. **Короткие префиксы (`c:`, `t:`)** вместо `concept:`, `tech:`
2. **Без хранения путей** в узлах и рёбрах - пути строятся динамически
3. **Упрощённая структура рёбер** - одно поле `source` вместо массива `evidence`
4. **Проекты в рёбрах** - массив `_key` проектов для компактности

### Инструменты

1. **Graphviz** - основной метод визуализации (качество + универсальность)
2. **Tom-Select** - лучший UX для выбора стартовой вершины
3. **Динамический сервер** - обновление графа без перезапуска

---

## 📝 Созданные файлы

### В проекте fedoc

**Визуализации:**
- `common-project-graph.dot` (5.7 KB) - Graphviz DOT
- `common-project-graph.png` (250 KB) - PNG изображение
- `common-project-graph.svg` (37 KB) - SVG изображение
- `common-project-graph.mmd` (2.9 KB) - Mermaid диаграмма
- `common-project-graph-fepro.txt` (5.8 KB) - текстовое дерево FEPRO
- `common-project-graph-femsq.txt` (2.9 KB) - текстовое дерево FEMSQ

**Документация:**
- `GRAPH-VISUALIZATION.md` - инструкции по визуализации
- `docs/project-history/chat-2025-10-14-common-project-graph.md` - этот отчёт

### В arango-graph-viewer

**Обновлённые файлы:**
- `web_viewer.py` - добавлен Tom-Select
- `view-graph.sh` - переключён на динамический сервер

---

## 🎬 Заключение

### Достижения

Успешно создан **общий граф проектов** в ArangoDB:

1. ✅ **38 узлов** - полная структура технологических стеков
2. ✅ **62 рёбра** - все связи с распределением проектов
3. ✅ **DAG структура** - поддержка множественных путей для сбора правил
4. ✅ **Правильная архитектура** - иерархия зависимостей
5. ✅ **Инструменты визуализации** - 4 формата для разных задач
6. ✅ **Tom-Select восстановлен** - удобный выбор вершин с поиском

### Качество выполнения

- ✅ Структура отражает реальные зависимости проектов
- ✅ Безопасность правильно разделена (с/без)
- ✅ Альтернативные стеки показывают возможные варианты
- ✅ Минималистичная структура данных (экономия места)
- ✅ Отличные инструменты для работы с графом

### Готовность к следующему этапу

**Граф готов для:**
- Добавления правил к узлам
- Реализации алгоритма сбора правил (подъём вверх по DAG)
- Расширения элементами фронтенда (Vue.js, TypeScript, Quasar)
- Добавления новых проектов и технологий
- Интеграции с Cursor AI через MCP Server

**Текущий статус:** Общий граф проектов создан и готов к использованию ✅

**Следующий этап:** Добавление правил к узлам графа и реализация алгоритма сбора

---

## 📚 Полезные команды

### Просмотр графа

```bash
# Интерактивный просмотр с Tom-Select
cd /home/alex/tools/arango-graph-viewer && ./view-graph.sh

# Только проект FEPRO
./view-graph.sh --project fepro

# Графические файлы
xdg-open /home/alex/projects/rules/fedoc/common-project-graph.png
firefox /home/alex/projects/rules/fedoc/common-project-graph.svg

# Текстовое дерево
cat /home/alex/projects/rules/fedoc/common-project-graph-fepro.txt
```

### AQL запросы

```aql
-- Все узлы проекта FEPRO
FOR v, e IN 1..10 OUTBOUND 'canonical_nodes/c:backend'
    GRAPH 'common_project_graph'
    FILTER 'fepro' IN e.projects
    RETURN DISTINCT v

-- Технологии проекта FEMSQ
FOR v, e IN 1..10 OUTBOUND 'canonical_nodes/c:backend'
    GRAPH 'common_project_graph'
    FILTER 'femsq' IN e.projects AND v.kind == 'technology'
    RETURN DISTINCT v.name

-- Альтернативные стеки
FOR v, e IN 1..10 OUTBOUND 'canonical_nodes/c:backend'
    GRAPH 'common_project_graph'
    FILTER LENGTH(e.projects) == 0
    RETURN DISTINCT v
```

---

**Дата создания:** 2025-10-14  
**Автор отчёта:** Claude (Cursor AI)  
**Проверено:** Александр  
**Статус:** Завершён, граф готов к использованию

**Следующий чат:** Добавление правил к узлам графа

