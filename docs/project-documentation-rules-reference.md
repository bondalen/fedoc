# Справочник по системе ссылок fedoc

**Версия:** 1.0.0  
**Дата:** 2025-10-14  
**Автор:** Александр

---

## Формат ссылок

Все ссылки используют формат `type:path`, где путь строится из ID элементов через точку (для Python модулей) или простое имя (для компонентов).

---

## Таблица форматов

| Тип | Формат | Пример |
|-----|--------|--------|
| **Компоненты системы** |
| Компонент | `component:name` | `component:mcp-server` |
| Python модуль | `module:path.to.module` | `module:mcp_server.handlers.graph_visualizer` |
| Python класс | `class:module.ClassName` | `class:graph_viewer.viewer.ArangoGraphViewer` |
| **База данных ArangoDB** |
| Коллекция | `collection:name` | `collection:projects` |
| Граф | `graph:name` | `graph:common_project_graph` |
| **Планирование** |
| Задача | `task:id` | `task:0004` |
| Дерево | `tree:number` | `tree:01` |
| Пункт структуры | `item:tree.structure` | `item:01.01.01` |
| **Журнал** |
| Чат | `chat:id` | `chat:chat-2025-10-14-001` |
| Лог | `log:id` | `log:log-2025-10-14-001` |
| **Документация** |
| ADR | `adr:number` | `adr:001` |
| Feature | `feature:id` | `feature:graph-visualization` |
| **Инструменты** |
| CLI инструмент | `tool:name` | `tool:view-graph` |
| MCP команда | `command:name` | `command:show_graph` |

---

## Примеры использования

### В project-development.json

```json
{
  "task": {
    "task-attributes": {
      "links": {
        "projectDocsRefs": [
          "component:graph-viewer",
          "module:lib.graph_viewer.viewer",
          "class:graph_viewer.viewer.ArangoGraphViewer",
          "collection:canonical_nodes"
        ],
        "journalRefs": [
          "chat:chat-2025-10-14-001",
          "log:log-2025-10-14-001"
        ],
        "decisionRefs": [
          "adr:003"
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
          "component:mcp-server",
          "module:mcp_server.handlers.graph_visualizer",
          "tool:view-graph"
        ],
        "developmentTasks": [
          "task:0004"
        ],
        "decisionRefs": [
          "adr:002"
        ]
      }
    }
  }
}
```

### В project-docs.json

```json
{
  "mcp-server": {
    "name": "fedoc MCP Server",
    "location": "src/mcp_server",
    "commands": [
      "show_graph",
      "query_graph",
      "get_rules"
    ],
    "links": {
      "dependencies": [
        "component:graph-viewer",
        "component:database"
      ],
      "decisionRefs": [
        "adr:002"
      ]
    }
  }
}
```

---

## Правила формирования ID

### Для компонентов системы
- **Формат:** kebab-case
- **Примеры:** `mcp-server`, `graph-viewer`, `database`

### Для Python модулей
- **Формат:** snake_case (как в Python)
- **Полный путь от src/**
- **Примеры:**
  - `mcp_server.server`
  - `mcp_server.handlers.graph_visualizer`
  - `lib.graph_viewer.viewer`
  - `lib.graph_viewer.web_viewer`

### Для Python классов
- **Формат:** PascalCase (как в Python)
- **С указанием модуля**
- **Примеры:**
  - `graph_viewer.viewer.ArangoGraphViewer`
  - `mcp_server.server.FedocServer`

### Для коллекций и графов ArangoDB
- **Формат:** snake_case
- **Множественное число для коллекций**
- **Примеры:**
  - `projects`
  - `canonical_nodes`
  - `project_edges`
  - `common_project_graph`

### Для задач
- **Формат:** Сквозная нумерация `0001`, `0002`, `0003`...
- **4 цифры для задач**

### Для чатов и логов
- **Формат:** `chat-YYYY-MM-DD-NNN` или `log-YYYY-MM-DD-NNN`
- **Примеры:** 
  - `chat-2025-10-14-001`
  - `log-2025-10-14-reorg`
  - `chat-2025-10-14-graph-visualization`

### Для ADR
- **Формат:** `adr:NNN` (трёхзначный номер)
- **Примеры:** `adr:001`, `adr:002`, `adr:003`

### Для инструментов
- **Формат:** kebab-case
- **Краткое описательное имя**
- **Примеры:**
  - `view-graph`
  - `db-manager`
  - `deploy-to-server`

---

## Преимущества

- ✅ **Устойчивость** - не зависит от порядка элементов в массивах
- ✅ **Уникальность** - путь через точку гарантирует уникальность
- ✅ **Читаемость** - понятна структура и местоположение
- ✅ **Соответствие коду** - похоже на пути Python модулей
- ✅ **Гибкость** - можно ссылаться на любой уровень иерархии
- ✅ **Масштабируемость** - легко добавлять новые типы ссылок

---

## Алгоритм разрешения ссылки

```python
def resolve_reference(ref: str) -> dict:
    """
    Разрешает ссылку формата type:path в объект документации.
    """
    type_name, path = ref.split(':', 1)
    
    match type_name:
        case 'component':
            return find_component_by_name(path)
            
        case 'module':
            # path = "mcp_server.handlers.graph_visualizer"
            return find_python_module(path)
            
        case 'class':
            # path = "graph_viewer.viewer.ArangoGraphViewer"
            module_path, class_name = path.rsplit('.', 1)
            module = find_python_module(module_path)
            return find_class_in_module(module, class_name)
            
        case 'task':
            return tasks['items'][path]
            
        case 'collection':
            return database.collections.find(name=path)
            
        case 'graph':
            return database.graphs.find(name=path)
            
        case 'chat' | 'log':
            return find_in_journal(path)
            
        case 'adr':
            return find_adr_document(path)
            
        case 'tool':
            return find_cli_tool(path)
```

---

## Особые случаи

### Модули с одинаковыми именами

**Проблема:** В разных пакетах могут быть модули с одинаковыми именами.

**Решение:** Полный путь делает их уникальными:
- `module:mcp_server.handlers.graph_visualizer`
- `module:lib.graph_viewer.viewer`

### Ссылка на группу артефактов

**На весь компонент:**
```json
"projectDocsRefs": ["component:mcp-server"]
```

**На все инструменты в директории:**
```json
"projectDocsRefs": ["tool:view-graph", "tool:db-manager"]
```

### Ссылка на схему данных

**На коллекцию и граф вместе:**
```json
"projectDocsRefs": [
  "collection:projects",
  "collection:canonical_nodes",
  "graph:common_project_graph"
]
```

---

## Специфика fedoc

### Инфраструктурные ссылки

Для инфраструктурных проектов характерны ссылки на:

1. **Библиотеки** (переиспользуемый код):
   ```json
   "projectDocsRefs": [
     "module:lib.graph_viewer.viewer",
     "class:graph_viewer.viewer.ArangoGraphViewer"
   ]
   ```

2. **Интеграции** (MCP, CLI):
   ```json
   "projectDocsRefs": [
     "component:mcp-server",
     "command:show_graph",
     "tool:view-graph"
   ]
   ```

3. **Схемы данных** (структуры в БД):
   ```json
   "projectDocsRefs": [
     "collection:projects",
     "graph:common_project_graph"
   ]
   ```

4. **Решения** (ADR):
   ```json
   "decisionRefs": [
     "adr:001",
     "adr:002",
     "adr:003"
   ]
   ```

### Связи между компонентами

```json
{
  "mcp-server": {
    "links": {
      "uses": [
        "component:graph-viewer",
        "module:lib.graph_viewer.web_viewer"
      ],
      "provides": [
        "command:show_graph",
        "command:query_graph"
      ]
    }
  },
  "graph-viewer": {
    "links": {
      "uses": [
        "collection:canonical_nodes",
        "graph:common_project_graph"
      ],
      "usedBy": [
        "component:mcp-server",
        "tool:view-graph"
      ]
    }
  }
}
```

---

## Рекомендации по использованию

### При создании нового компонента
1. Определите тип артефакта (component, module, class, tool)
2. Выберите подходящее имя в правильном формате
3. Создайте ссылки на зависимости
4. Добавьте ADR если решение значимое

### При документировании задачи
1. Укажите все затрагиваемые компоненты
2. Добавьте ссылки на ADR если есть
3. Свяжите с записями журнала
4. Укажите инструменты разработки

### При ведении журнала
1. Ссылайтесь на конкретные модули/классы
2. Указывайте задачи, которые выполнялись
3. Добавляйте ссылки на новые ADR
4. Фиксируйте используемые инструменты

---

**Документ создан:** 2025-10-14  
**Ответственный:** Александр

