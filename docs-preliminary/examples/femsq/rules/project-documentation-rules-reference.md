# Справочник по системе ссылок FEMSQ

**Версия:** 1.0.0  
**Дата:** 2025-10-09  
**Автор:** Александр

---

## Формат ссылок

Все ссылки используют формат `type:path`, где путь строится из ID элементов через точку.

---

## Таблица форматов

| Тип | Формат | Пример |
|-----|--------|--------|
| **Артефакты кода** |
| Модуль | `module:id` | `module:backend` |
| Компонент | `component:module.component` | `component:backend.database-config` |
| Класс | `class:module.component.class` | `class:backend.database-config.DatabaseConfigService` |
| Вложенный класс | `class:module.component.class.nested` | `class:backend.config.Service.Validator` |
| **База данных** |
| Таблица | `table:name` | `table:contractors` |
| **Планирование** |
| Задача | `task:id` | `task:0004` |
| Дерево | `tree:number` | `tree:01` |
| Пункт структуры | `item:tree.structure` | `item:01.01.01` |
| **Журнал** |
| Чат | `chat:id` | `chat:chat-2025-10-09-001` |
| Лог | `log:id` | `log:log-2025-10-09-001` |
| **Другое** |
| Feature | `feature:id` | `feature:database-connection` |
| Правило AI | `rule:id` | `rule:coding-standards` |

---

## Примеры использования

### В project-development.json

```json
{
  "task": {
    "task-attributes": {
      "links": {
        "projectDocsRefs": [
          "class:backend.database-config.DatabaseConfigService",
          "table:contractors"
        ],
        "journalRefs": [
          "chat:chat-2025-10-09-001",
          "log:log-2025-10-09-001"
        ]
      }
    }
  }
}
```

### В project-journal.json

```json
{
  "log": {
    "log-attributes": {
      "links": {
        "projectDocsRefs": [
          "class:backend.database-config.DatabaseConfigService"
        ],
        "developmentTasks": [
          "task:0004"
        ]
      }
    }
  }
}
```

---

## Правила формирования ID

### Для модулей и компонентов
- **Формат:** kebab-case
- **Примеры:** `backend`, `database-config`, `user-auth`

### Для классов
- **Формат:** PascalCase (как в коде)
- **Примеры:** `DatabaseConfigService`, `ConnectionManager`, `UserRepository`

### Для таблиц
- **Формат:** snake_case (как в БД)
- **Множественное число**
- **Примеры:** `contractors`, `users`, `order_items`

### Для задач
- **Формат:** Сквозная нумерация `0001`, `0002`, `0003`...

### Для чатов и логов
- **Формат:** `chat-YYYY-MM-DD-NNN` или `log-YYYY-MM-DD-NNN`
- **Примеры:** `chat-2025-10-09-001`, `log-2025-10-09-001`

---

## Преимущества

- ✅ **Устойчивость** - не зависит от порядка элементов в массивах
- ✅ **Уникальность** - путь через точку гарантирует уникальность
- ✅ **Читаемость** - понятна структура и местоположение
- ✅ **Соответствие коду** - похоже на пути пакетов Java
- ✅ **Гибкость** - можно ссылаться на любой уровень иерархии
- ✅ **Масштабируемость** - легко добавлять новые типы ссылок

---

## Алгоритм разрешения ссылки

```javascript
function resolveReference(ref) {
  const [type, path] = ref.split(':', 2);
  const parts = path.split('.');
  
  switch(type) {
    case 'module':
      return findModuleById(parts[0]);
      
    case 'component':
      const module = findModuleById(parts[0]);
      return findComponentInModule(module, parts[1]);
      
    case 'class':
      const mod = findModuleById(parts[0]);
      const comp = findComponentInModule(mod, parts[1]);
      let currentClass = findClassInComponent(comp, parts[2]);
      
      // Обработка вложенных классов
      for (let i = 3; i < parts.length; i++) {
        currentClass = findNestedClass(currentClass, parts[i]);
      }
      return currentClass;
      
    case 'task':
      return tasks.items[path];
      
    case 'table':
      return database.tables.find(t => t.name === path);
      
    case 'chat':
    case 'log':
      return findInJournal(path);
  }
}
```

---

## Особые случаи

### Артефакты с одинаковыми именами

**Проблема:** В разных модулях могут быть классы с одинаковыми именами.

**Решение:** Иерархический путь делает их уникальными:
- `class:backend.config.Service`
- `class:frontend.config.Service`

### Ссылка на группу артефактов

**На весь компонент:**
```json
"projectDocsRefs": ["component:backend.database-config"]
```

**На весь модуль:**
```json
"projectDocsRefs": ["module:backend"]
```

---

**Документ создан:** 2025-10-09  
**Ответственный:** Александр
