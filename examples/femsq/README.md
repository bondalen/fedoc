# FEMSQ - Эталонный пример документации

**Проект:** [FEMSQ](https://github.com/bondalen/femsq) (Fish Eye MS SQL Server)  
**Назначение:** Система работы с контрагентами при капитальном строительстве  
**Статус:** Эталонный пример для системы fedoc

---

## 📋 О проекте FEMSQ

FEMSQ - это full-stack система на:
- **Backend:** Spring Boot 3.4.5 + Java 21 + GraphQL
- **Frontend:** Vue.js 3.4.21 + Quasar + TypeScript
- **БД:** MS SQL Server (внешняя корпоративная)

Проект имеет проработанную систему документации на основе JSON-файлов, которая послужила основой для создания fedoc.

---

## 📁 Структура примера

### original/
Оригинальные JSON-файлы документации FEMSQ:

- **project-docs.json** - проектная документация
  - Метаданные, архитектура, технологический стек
  - Ссылки на модули в extensions
  - Схема базы данных, deployment
  
- **project-development.json** - планирование v2.0
  - DAG-структура с разделением задач и деревьев
  - 10 задач с критериями завершения
  - 3 дерева структуры (артефакты, функционал, модули)
  
- **project-journal.json** - журнал разработки
  - Иерархия чат → лог → действие
  - Хронологический порядок
  - Ссылки на задачи и артефакты

- **modules/** - структура модулей
  - modules.json - рекурсивная иерархия модулей
  - modules-example.json - образец структуры

### rules/
Правила ведения документации FEMSQ:

- **project-documentation-rules.md** - общие правила
- **project-docs-json-rules.md** - правила для project-docs.json
- **project-development-json-rules.md** - правила для development
- **project-journal-json-rules.md** - правила для journal
- **project-documentation-rules-reference.md** - справочник ссылок
- **project-documentation-rules-structural-numbering.md** - система нумерации

---

## 🧱 Ключевые паттерны FEMSQ

### 1. Рекурсивная структура модулей
```
Module → Module → Component → Component → Class → Class
```

### 2. DAG-структура задач
```
Задача 0004 присутствует в 3 деревьях:
- Tree 01 (артефакты): 01.01.01.01
- Tree 02 (функционал): 02.01.01
- Tree 0a (модули): 0a.01.01
```

### 3. Система ссылок type:path
```
class:backend.database-config.DatabaseConfigurationService
component:backend.database-config
module:backend
table:contractors
task:0004
```

### 4. Структурная нумерация 01-zz
```
01-99 (99) → 0a-9z (260) → a0-z9 (260) → aa-zz (676)
Итого: 1,295 позиций на уровень
```

---

## 🎯 Использование

FEMSQ используется в fedoc для:

1. **Извлечения шаблонов** для новых проектов
2. **Демонстрации возможностей** системы документации
3. **Тестирования миграции** и извлечения блоков
4. **Обучения** - как пример правильной документации

---

## 🔗 Ссылки

- **Репозиторий FEMSQ:** https://github.com/bondalen/femsq
- **Репозиторий fedoc:** https://github.com/bondalen/fedoc
- **История создания fedoc:** [../docs/project-history/chat-2025-01-27-28-inception.md](../../docs/project-history/chat-2025-01-27-28-inception.md)

---

**Дата копирования:** 2025-01-28  
**Источник:** FEMSQ commit 73e3889  
**Автор оригинала:** Александр
