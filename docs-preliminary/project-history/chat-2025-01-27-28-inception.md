# История создания проекта fedoc

**Дата:** 2025-01-27 - 2025-01-28  
**Чат:** Inception (создание проекта)  
**Участники:** Александр, Claude (Cursor AI)  
**Проект-источник:** [femsq](https://github.com/bondalen/femsq)

---

## 📋 Контекст начала работы

### Ситуация перед чатом

В проекте **FEMSQ** (Fish Eye MS SQL Server) была разработана система документации на основе JSON-файлов:
- `project-docs.json` - проектная документация с модулями
- `project-development.json` v2.0 - планирование с DAG-структурой задач
- `project-journal.json` - журнал разработки

Система имела:
- ✅ 4 уровня абстракции (мета-паттерны, блоки, правила, расширения)
- ✅ Систему ссылок `type:path`
- ✅ Структурную нумерацию `01-zz`
- ✅ DAG-структуру для задач

### Возникшая идея

Создать **централизованную систему** для:
- Хранения общих "строительных блоков" документации
- Переиспользования решений между проектами
- Накопления знаний без повторной адаптации

---

## 💬 Ход обсуждения

### Этап 1: Формулирование концепции

**Вопрос:** Как создать общую для группы проектов базу правил и документации?

**Обсуждение:**
- Необходимость NoSQL базы данных
- Разделение на общую базу знаний и конкретные проекты
- Декомпозиция на "строительные блоки"

### Этап 2: Выбор технологии

**Рассмотрены варианты:**
- MongoDB - хорош для JSON, но слабая поддержка графов
- PostgreSQL + JSONb - требует расширений для графов
- Neo4j - отличные графы, но не nativ JSON
- **ArangoDB** ✅ - выбран как оптимальный

**Причины выбора ArangoDB:**
1. Multi-Model (Document + Graph + Key-Value)
2. Нативная поддержка DAG для задач
3. Apache 2.0 - полностью open-source и бесплатно
4. Web UI с визуализацией графов
5. Python драйвер `python-arango`

### Этап 3: Архитектура

**Принятые решения:**

1. **Развертывание:**
   - Локально: Docker Compose
   - Production: Удалённая VM (cloud.ru)
   - Без API на первом этапе

2. **Работа из Cursor AI:**
   - Вариант A: MCP Server (рекомендуется)
   - Вариант B: Python скрипты в Terminal
   - Вариант C: Web UI ArangoDB

3. **Структура БД:**
   - Layer 1: Templates (meta_patterns, structural_blocks, system_rules)
   - Layer 2: Projects (tasks, modules, components, classes)
   - Edge Collections: inTree, dependsOn, basedOnTemplate
   - Graphs: project_structure, task_dag, knowledge_graph

### Этап 4: Декомпозиция на блоки

**4 уровня абстракции:**

1. **Meta-паттерны** - универсальные для всех элементов
   - displayName pattern: `[emoji] [name] (status, priority). № [id]`
   - attributes pattern: группировка в `*-attributes`
   - artifact pattern: физические атрибуты
   - links pattern: система ссылок `type:path`

2. **Структурные блоки** - переиспользуемые элементы
   - Module block (рекурсивный)
   - Component block (рекурсивный)
   - Class block (рекурсивный)
   - Task-DAG block (с множественными связями)
   - Tree block (для иерархии)
   - Chat/Log block (для журнала)

3. **Системные правила** - общие для всех
   - Structural numbering (01-zz, 1295 позиций)
   - Type:path references (устойчивые ссылки)
   - Status system (с эмодзи)
   - Completion criteria (вместо времени)

4. **Доменные расширения** - специфика технологий
   - Maven extension (pom.xml, packaging)
   - Spring Boot extension (@Service, @Configuration)
   - MS SQL extension (типы данных, аутентификация)

### Этап 5: Проверка удалённого сервера

**Сервер:** 176.108.244.252 (cloud.ru)

**Проведённый анализ:**
- ✅ SSH доступ: работает
- ⚠️ Uptime: 47 дней (требуется перезагрузка)
- ⚠️ Обновления: 48 пакетов (не применены с октября 2024)
- ⚠️ Ядро: 5.15.0-133 → доступно 5.15.0-157
- ⚠️ Артефакты vuege: требуют очистки (~3.2 GB)

**Ресурсы:**
- RAM: 3.8 GB (доступно 2.6 GB) ✅
- Диск: 30 GB (свободно 22 GB) ✅
- Docker: установлен ✅
- Python 3.10.12: установлен ✅

**Решения:**
1. Очистить артефакты vuege
2. Обновить систему
3. Перезагрузить сервер
4. Подготовить к развертыванию fedoc

### Этап 6: Разделение проектов

**Ключевое решение:**
- **femsq** остаётся эталонным примером (без изменений)
- **fedoc** - новый независимый проект системы документации

**Действия:**
1. Откатить femsq к состоянию до чата (коммит `73e3889`)
2. Создать fedoc с минимальной структурой
3. Перенести концепцию в fedoc
4. Скопировать документацию FEMSQ как образец
5. Создать отчёт о работе (этот документ)

---

## ✅ Принятые решения

### Технологические

| Решение | Вариант | Обоснование |
|---------|---------|-------------|
| **База данных** | ArangoDB Community | Multi-Model, графы, бесплатно |
| **Лицензия** | Apache 2.0 | Open-source, без ограничений |
| **Язык** | Python 3.10+ | Простота, python-arango |
| **Развертывание** | Docker Compose | Переносимость, изоляция |
| **API** | Нет (на первом этапе) | Минимализм, прямой доступ |
| **Интеграция** | MCP Server (Cursor) | Нативная работа из IDE |

### Архитектурные

1. **Декомпозиция:** 4 уровня абстракции (не просто копирование JSON)
2. **Развертывание:** Локально (Docker) → Production (VM)
3. **Работа из Cursor:** MCP Server или Python REPL
4. **Разделение:** femsq = пример, fedoc = система

### Организационные

1. **femsq:** эталонный проект, без изменений
2. **fedoc:** независимая разработка системы
3. **Сервер:** cloud.ru (176.108.244.252), после очистки и обновления
4. **Дальнейшая работа:** в новом чате проекта fedoc

---

## 📦 Что создано

### Структура fedoc

```
fedoc/
├── README.md
├── .gitignore
├── docs/
│   ├── concepts/
│   │   └── centralized-documentation-system-concept.md
│   └── project-history/
│       └── chat-2025-01-27-28-inception.md (этот документ)
└── examples/
    └── femsq/
        ├── original/
        │   ├── project-docs.json
        │   ├── project-docs-example.json
        │   ├── project-development.json
        │   ├── project-development-example.json
        │   ├── project-journal.json
        │   ├── project-journal-example.json
        │   └── modules/
        │       ├── modules.json
        │       └── modules-example.json
        └── rules/
            ├── project-documentation-rules.md
            ├── project-docs-json-rules.md
            ├── project-development-json-rules.md
            ├── project-journal-json-rules.md
            ├── project-documentation-rules-reference.md
            └── project-documentation-rules-structural-numbering.md
```

### Документация FEMSQ как образец

Скопирована полная документация:
- ✅ JSON файлы (проект, разработка, журнал)
- ✅ Примеры (project-docs-example.json и др.)
- ✅ Модули (modules.json с рекурсивной структурой)
- ✅ Правила ведения документации

**Назначение:** Эталонный пример для:
- Анализа структуры
- Извлечения паттернов
- Создания шаблонов
- Тестирования миграции

---

## 🎯 Текущий статус

### Выполнено

- ✅ Концепция разработана и задокументирована
- ✅ Технология выбрана (ArangoDB)
- ✅ Архитектура спроектирована
- ✅ Проект fedoc создан
- ✅ Документация FEMSQ скопирована
- ✅ femsq возвращён в чистое состояние
- ✅ Отчёт о работе создан

### На сервере (176.108.244.252)

- ✅ Очистка vuege (~3.2 GB)
- ✅ Обновление системы (48 пакетов)
- ✅ Перезагрузка (новое ядро 5.15.0-157)
- ⏳ Клонирование fedoc (в новом чате)
- ⏳ Развертывание ArangoDB (в новом чате)

---

## 🚀 Следующие шаги (для нового чата fedoc)

### 1. Создание полной структуры

```bash
fedoc/
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── arango/init/
├── scripts/
│   ├── core/
│   ├── migration/
│   ├── extraction/
│   ├── query/
│   ├── sync/
│   └── cli/
├── mcp/
│   └── fedoc_mcp_server.py
├── schemas/
│   ├── meta-patterns/
│   ├── structural-blocks/
│   └── system-rules/
└── templates/
    └── extracted/femsq/
```

### 2. Развертывание на сервере

```bash
# На 176.108.244.252
cd /home/user1
git clone https://github.com/bondalen/fedoc.git
cd fedoc/docker
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Миграция FEMSQ

```bash
# Написать migrator
scripts/migration/femsq_migrator.py

# Запустить миграцию
python -m cli.fedoc_cli migrate femsq ../examples/femsq/original/
```

### 4. Извлечение строительных блоков

```bash
# Анализ паттернов FEMSQ
python -m extraction.block_extractor extract femsq

# Результат: templates/extracted/femsq/
```

### 5. MCP Server для Cursor

```bash
# Реализовать MCP Server
mcp/fedoc_mcp_server.py

# Настроить в Cursor
# .cursor/mcp_settings.json
```

### 6. Тестирование

```bash
# Создать новый проект из шаблонов FEMSQ
python -m cli.fedoc_cli create "Test Project" --template femsq
```

---

## 📚 Ключевые документы

### В fedoc

- [Концепция системы](../concepts/centralized-documentation-system-concept.md)
- [Этот документ](chat-2025-01-27-28-inception.md)

### В FEMSQ (образцы)

- [Правила документации](../../examples/femsq/rules/project-documentation-rules.md)
- [Правила project-docs.json](../../examples/femsq/rules/project-docs-json-rules.md)
- [Правила project-development.json](../../examples/femsq/rules/project-development-json-rules.md)
- [Правила project-journal.json](../../examples/femsq/rules/project-journal-json-rules.md)
- [Система ссылок](../../examples/femsq/rules/project-documentation-rules-reference.md)
- [Структурная нумерация](../../examples/femsq/rules/project-documentation-rules-structural-numbering.md)

### Внешние ресурсы

- **ArangoDB:** https://www.arangodb.com/
- **python-arango:** https://github.com/ArangoDB-Community/python-arango
- **FEMSQ:** https://github.com/bondalen/femsq
- **fedoc:** https://github.com/bondalen/fedoc

---

## 💡 Уроки и инсайты

### Что сработало хорошо

1. **Использование FEMSQ как основы** - готовая проработанная система документации
2. **Выбор ArangoDB** - идеальное решение для DAG + JSON
3. **Декомпозиция на блоки** - чёткое разделение уровней абстракции
4. **Минимализм** - без API на первом этапе
5. **Разделение проектов** - femsq остаётся эталоном, fedoc развивается независимо

### Ключевые решения

1. **Не MongoDB, а ArangoDB** - графы критичны для DAG
2. **MCP Server вместо API** - прямая интеграция с Cursor
3. **Docker Compose** - простое развертывание
4. **Python** - простота и гибкость

### Риски

1. **Сложность изучения ArangoDB** - требуется время на освоение
2. **Vendor lock-in** - зависимость от ArangoDB
3. **Поддержка двух систем** - JSON + ArangoDB на переходе
4. **Неопределённость эффективности** - выгода только при втором проекте

---

## 🎬 Заключение

Проект **fedoc** создан как результат анализа и развития системы документации из FEMSQ. 

**Основная идея:** Превратить успешный подход к документации одного проекта в универсальную систему для группы проектов.

**Ключевая ценность:** Переиспользование "строительных блоков" документации без необходимости каждый раз адаптировать правила и структуры.

**Текущий этап:** Минимальная инициализация проекта завершена. Основная работа начинается в новом чате fedoc.

---

**Дата создания документа:** 2025-01-28  
**Автор:** Claude (Cursor AI)  
**Статус:** Завершён, готов для нового чата

**Следующий чат:** Разработка fedoc (docker, scripts, mcp, deployment)
