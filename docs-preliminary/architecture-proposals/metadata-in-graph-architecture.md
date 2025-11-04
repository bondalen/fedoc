# Архитектура: Метаданные классов в графе

**Дата**: 2025-11-04  
**Статус**: Предложение  
**Приоритет**: Высокий

---

## Концепция

Хранить определения всех классов проекта (фронтенд и бакенд) в самом графе как специальные метаузлы. Граф становится единственным источником истины для структуры данных проекта.

**Философия fedoc**: На клиентской машине хранятся только настройки подключения и секреты. Вся информация о проекте и его структуре — в графе.

---

## Новые типы узлов

### Расширение системы префиксов

```
Существующие:
- c:* (concept) — концепты проекта
- t:* (technology) — технологии
- v:* (version) — версии технологий

Новые:
- m:* (meta) — метаданные общего назначения
- cls:* (class-def) — определение класса
- prop:* (property-def) — определение свойства класса
- meth:* (method-def) — определение метода класса
- rel:* (relation-def) — определение связи между классами
```

---

## Структура метаузлов в графе

### Полная иерархия

```
c:project (fedoc)
  c:dev-objects (Объекты разработки)
    c:meta (Метаданные проекта) 🆕
      
      # === СИСТЕМА КЛАССОВ ===
      c:class-system (Система классов) 🆕
        
        # Базовые классы
        cls:GraphObject (Класс: GraphObject)
          properties: {
            abstract: true,
            description: "Базовый класс для всех объектов графа",
            backend_module: "models.base",
            frontend_module: "models/base.js"
          }
          ├─→ prop:GraphObject.id
          │     properties: {type: "string", required: true}
          ├─→ prop:GraphObject.created_at
          │     properties: {type: "datetime", required: false}
          ├─→ prop:GraphObject.updated_at
          │     properties: {type: "datetime", required: false}
          ├─→ meth:GraphObject.to_dict
          │     properties: {returns: "dict", description: "Сериализация в словарь"}
          ├─→ meth:GraphObject.from_dict
          │     properties: {returns: "GraphObject", static: true}
          ├─→ meth:GraphObject.validate
          │     properties: {returns: "bool", description: "Валидация данных"}
          └─→ meth:GraphObject.to_json
                properties: {returns: "string", description: "Сериализация в JSON"}
        
        cls:GraphVertex (Класс: GraphVertex)
          properties: {
            extends: "cls:GraphObject",
            abstract: true,
            backend_module: "models.vertices.graph_vertex",
            frontend_module: "models/vertices/GraphVertex.js"
          }
          ├─→ prop:GraphVertex.key
          │     properties: {type: "string", required: true, pattern: "^[ctv]:.+"}
          ├─→ prop:GraphVertex.label
          │     properties: {type: "string", required: true}
          ├─→ prop:GraphVertex.node_type
          │     properties: {type: "enum", values: ["concept", "technology", "version", "default"]}
          ├─→ meth:GraphVertex.infer_type
          │     properties: {returns: "string", description: "Определить тип по ключу"}
          ├─→ meth:GraphVertex.get_visual_style
          │     properties: {returns: "dict", params: {theme: "string"}}
          ├─→ meth:GraphVertex.to_vis_format
          │     properties: {returns: "dict", description: "Формат для vis-network"}
          └─→ meth:GraphVertex.to_svg_format
                properties: {returns: "string", description: "Формат для SVG"}
        
        cls:GraphEdge (Класс: GraphEdge)
          properties: {
            extends: "cls:GraphObject",
            backend_module: "models.edges.graph_edge",
            frontend_module: "models/edges/GraphEdge.js"
          }
          ├─→ prop:GraphEdge.from_id
          │     properties: {type: "string", required: true}
          ├─→ prop:GraphEdge.to_id
          │     properties: {type: "string", required: true}
          ├─→ prop:GraphEdge.edge_type
          │     properties: {type: "enum", values: ["uses", "depends", "related", "contains"]}
          ├─→ prop:GraphEdge.projects
          │     properties: {type: "array", items: "string"}
          ├─→ meth:GraphEdge.get_visual_style
          └─→ meth:GraphEdge.to_vis_format
        
        # Специализированные классы вершин
        cls:ConceptVertex (Класс: ConceptVertex)
          properties: {
            extends: "cls:GraphVertex",
            node_type: "concept",
            key_prefix: "c:",
            backend_module: "models.vertices.concept_vertex",
            frontend_module: "models/vertices/ConceptVertex.js"
          }
        
        cls:TechnologyVertex (Класс: TechnologyVertex)
          properties: {
            extends: "cls:GraphVertex",
            node_type: "technology",
            key_prefix: "t:",
            backend_module: "models.vertices.technology_vertex",
            frontend_module: "models/vertices/TechnologyVertex.js"
          }
          ├─→ prop:TechnologyVertex.version
          │     properties: {type: "string"}
          └─→ prop:TechnologyVertex.official_site
                properties: {type: "url"}
        
        cls:VersionVertex (Класс: VersionVertex)
          properties: {
            extends: "cls:GraphVertex",
            node_type: "version",
            key_prefix: "v:",
            backend_module: "models.vertices.version_vertex",
            frontend_module: "models/vertices/VersionVertex.js"
          }
        
        # === БИЗНЕС-КЛАССЫ ===
        
        cls:Project (Класс: Project) 🎯
          properties: {
            extends: "cls:ConceptVertex",
            key_pattern: "^c:project$",
            backend_module: "models.business.project",
            frontend_module: "models/business/Project.js",
            description: "Проект в системе fedoc"
          }
          # Свойства
          ├─→ prop:Project.name
          │     properties: {type: "string", required: true, description: "Название проекта"}
          ├─→ prop:Project.description
          │     properties: {type: "string", description: "Описание проекта"}
          ├─→ prop:Project.repository_url
          │     properties: {type: "url", description: "URL репозитория"}
          ├─→ prop:Project.tech_stack
          │     properties: {type: "array", items: "string", description: "Стек технологий"}
          # Связи
          ├─→ rel:Project.has_backends
          │     properties: {
          │       type: "one_to_many",
          │       target: "cls:Backend",
          │       edge_type: "contains",
          │       description: "Бакенды проекта"
          │     }
          ├─→ rel:Project.has_frontends
          │     properties: {type: "one_to_many", target: "cls:Frontend", edge_type: "contains"}
          ├─→ rel:Project.uses_technologies
          │     properties: {type: "many_to_many", target: "cls:TechnologyVertex", edge_type: "uses"}
          # Методы
          ├─→ meth:Project.get_backends
          │     properties: {
          │       returns: "List[Backend]",
          │       description: "Получить все бакенды проекта",
          │       lazy: true,
          │       params: {repository: "optional"}
          │     }
          ├─→ meth:Project.add_backend
          │     properties: {
          │       returns: "void",
          │       params: {backend: "Backend", repository: "optional"}
          │     }
          └─→ meth:Project.get_technology_stack
                properties: {
                  returns: "List[string]",
                  description: "Полный стек технологий (включая дочерние)",
                  lazy: true
                }
        
        cls:Backend (Класс: Backend) 🎯
          properties: {
            extends: "cls:ConceptVertex",
            key_pattern: "^c:backend",
            backend_module: "models.business.backend",
            frontend_module: "models/business/Backend.js",
            description: "Бакенд проекта"
          }
          ├─→ prop:Backend.framework
          │     properties: {type: "string", description: "Фреймворк (например, Flask, Spring Boot)"}
          ├─→ prop:Backend.database
          │     properties: {type: "string", description: "База данных"}
          ├─→ prop:Backend.api_type
          │     properties: {
          │       type: "enum",
          │       values: ["REST", "GraphQL", "gRPC"],
          │       default: "REST"
          │     }
          ├─→ rel:Backend.belongs_to_project
          │     properties: {type: "many_to_one", target: "cls:Project", edge_type: "contains", inverse: true}
          ├─→ rel:Backend.uses_technologies
          │     properties: {type: "many_to_many", target: "cls:TechnologyVertex", edge_type: "uses"}
          ├─→ meth:Backend.get_project
          │     properties: {returns: "Project", lazy: true}
          └─→ meth:Backend.get_technologies
                properties: {returns: "List[TechnologyVertex]", lazy: true}
        
        cls:Frontend (Класс: Frontend) 🎯
          properties: {
            extends: "cls:ConceptVertex",
            key_pattern: "^c:frontend",
            backend_module: "models.business.frontend",
            frontend_module: "models/business/Frontend.js"
          }
          ├─→ prop:Frontend.framework
          ├─→ prop:Frontend.build_tool
          └─→ rel:Frontend.belongs_to_project
      
      # === КОНФИГУРАЦИЯ ВИЗУАЛИЗАЦИИ ===
      c:visualization-config (Конфигурация визуализации) 🆕
        
        c:canvas-config (Конфигурация канвы)
          properties: {
            dark: {background: "#111"},
            light: {background: "#f5f5f5"}
          }
        
        c:node-styles (Стили узлов)
          c:category-style (Стиль: category)
            properties: {
              dark: {
                color: "#1976D2",
                border: "#0D47A1",
                shape: "box",
                size: {width: 120, height: 36, borderRadius: 6, borderWidth: 1, margin: 10},
                font: {color: "#ffffff", size: 12, strokeWidth: 2, strokeColor: "#1976D2"}
              },
              light: {
                color: "#E3F2FD",
                border: "#90CAF9",
                shape: "box",
                size: {width: 120, height: 36, borderRadius: 6, borderWidth: 1, margin: 10},
                font: {color: "#000000", size: 12, strokeWidth: 2, strokeColor: "#E3F2FD"}
              }
            }
          
          c:technology-style (Стиль: technology)
            properties: {
              dark: {
                color: "#388E3C",
                border: "#1B5E20",
                shape: "circle",
                size: {size: 36, borderWidth: 1, margin: 10},
                font: {color: "#ffffff", size: 12, strokeWidth: 2, strokeColor: "#388E3C"}
              },
              light: {
                color: "#E8F5E9",
                border: "#81C784",
                shape: "circle",
                size: {size: 36, borderWidth: 1, margin: 10},
                font: {color: "#000000", size: 12, strokeWidth: 2, strokeColor: "#E8F5E9"}
              }
            }
          
          c:version-style (Стиль: version)
            # ... аналогично
        
        c:edge-styles (Стили рёбер)
          c:smooth-config (Конфигурация кривизны)
            properties: {
              type: "cubicBezier",
              roundness: 0.5,
              forceDirection: "vertical"
            }
          
          c:uses-style (Стиль: uses)
            properties: {color: "#B0BEC5", dashes: false}
          
          c:depends-style (Стиль: depends)
            properties: {color: "#FF6F00", dashes: true}
        
        c:layout-config (Конфигурация раскладки)
          properties: {
            hierarchical: {
              enabled: true,
              direction: "UD",
              sortMethod: "directed",
              levelSeparation: 140,
              nodeSpacing: 180,
              treeSpacing: 240
            }
          }
        
        c:physics-config (Конфигурация физики)
          properties: {
            enabled: true,
            solver: "hierarchicalRepulsion",
            hierarchicalRepulsion: {
              nodeDistance: 160,
              springLength: 160,
              damping: 0.45,
              avoidOverlap: 1
            }
          }
        
        c:interaction-config (Конфигурация взаимодействия)
          properties: {
            hover: true,
            multiselect: true,
            zoomView: true,
            dragView: true
          }
      
      # === API КОНТРАКТ ===
      c:api-contract (API контракт) 🆕
        
        c:endpoint-get-graph (GET /api/graph)
          properties: {
            path: "/api/graph",
            method: "GET",
            description: "Получить граф проекта",
            params: {
              project: {type: "string", required: true},
              theme: {type: "string", enum: ["dark", "light"], default: "light"}
            },
            response: {
              type: "object",
              properties: {
                nodes: {type: "array", items: "GraphVertex"},
                edges: {type: "array", items: "GraphEdge"}
              }
            }
          }
        
        c:endpoint-create-vertex (POST /api/vertices)
          properties: {
            path: "/api/vertices",
            method: "POST",
            request_body: "GraphVertex",
            response: "GraphVertex"
          }
        
        # ... другие эндпоинты
```

---

## Интеграция с graph_traverse_down

### Расширение команды MCP

**Файл**: `src/mcp_server/handlers/graph_traverse_down.py`

```python
def handle_graph_traverse_down(project: str, include_metadata: bool = True) -> str:
    """
    Обход графа с опциональным включением метаданных
    
    Args:
        project: Ключ проекта (fedoc, fepro, femsq)
        include_metadata: Включить метаданные классов (по умолчанию True)
    
    Returns:
        Markdown документ с полной структурой проекта
    """
    output = []
    
    # 1. Обычная структура проекта
    output.append(f"# Проект: {project}\n")
    output.append(traverse_project_structure(project))
    
    # 2. Метаданные (если запрошено)
    if include_metadata:
        output.append("\n" + "="*80 + "\n")
        output.append("# МЕТАДАННЫЕ ПРОЕКТА\n")
        
        output.append("\n## Система классов\n")
        output.append(traverse_class_system())
        
        output.append("\n## Конфигурация визуализации\n")
        output.append(traverse_visualization_config())
        
        output.append("\n## API контракт\n")
        output.append(traverse_api_contract())
    
    return '\n'.join(output)

def traverse_class_system() -> str:
    """Обход системы классов"""
    # Найти узел c:class-system
    query = """
    SELECT id, key, name, properties
    FROM canonical_nodes
    WHERE key = 'c:class-system'
    """
    
    class_system = db.execute(query).fetchone()
    if not class_system:
        return "*Система классов не определена*"
    
    # Получить все классы
    classes = get_child_nodes(class_system['id'], prefix='cls:')
    
    output = []
    for cls in classes:
        output.append(format_class_definition(cls))
    
    return '\n'.join(output)

def format_class_definition(cls_node: dict) -> str:
    """Форматировать определение класса для AI"""
    props = cls_node.get('properties', {})
    
    lines = [
        f"### {cls_node['name']}",
        f"**Ключ**: `{cls_node['key']}`",
        ""
    ]
    
    # Метаданные класса
    if props.get('extends'):
        lines.append(f"**Наследует**: `{props['extends']}`")
    if props.get('abstract'):
        lines.append("**Абстрактный**: Да")
    if props.get('key_pattern'):
        lines.append(f"**Паттерн ключа**: `{props['key_pattern']}`")
    if props.get('backend_module'):
        lines.append(f"**Модуль (Python)**: `{props['backend_module']}`")
    if props.get('frontend_module'):
        lines.append(f"**Модуль (JS)**: `{props['frontend_module']}`")
    if props.get('description'):
        lines.append(f"\n{props['description']}")
    
    # Свойства класса
    properties = get_class_properties(cls_node['id'])
    if properties:
        lines.append("\n**Свойства**:")
        for prop in properties:
            prop_props = prop.get('properties', {})
            prop_type = prop_props.get('type', 'any')
            required = " *(обязательное)*" if prop_props.get('required') else ""
            description = f" — {prop_props['description']}" if prop_props.get('description') else ""
            lines.append(f"- `{prop['name']}`: {prop_type}{required}{description}")
    
    # Методы класса
    methods = get_class_methods(cls_node['id'])
    if methods:
        lines.append("\n**Методы**:")
        for method in methods:
            meth_props = method.get('properties', {})
            returns = meth_props.get('returns', 'void')
            params_dict = meth_props.get('params', {})
            params = ', '.join([f"{k}: {v}" for k, v in params_dict.items()])
            description = meth_props.get('description', '')
            
            lines.append(f"- `{method['name']}({params})` → `{returns}`")
            if description:
                lines.append(f"  {description}")
    
    # Связи класса
    relations = get_class_relations(cls_node['id'])
    if relations:
        lines.append("\n**Связи**:")
        for rel in relations:
            rel_props = rel.get('properties', {})
            rel_type = rel_props.get('type', 'unknown')
            target = rel_props.get('target', 'unknown')
            edge_type = rel_props.get('edge_type', '')
            edge_info = f" (через `{edge_type}`)" if edge_type else ""
            lines.append(f"- `{rel['name']}`: {rel_type} → `{target}`{edge_info}")
    
    lines.append("")  # Пустая строка между классами
    return '\n'.join(lines)

def get_class_properties(class_id: int) -> list:
    """Получить свойства класса"""
    query = """
    SELECT v.id, v.key, v.name, v.properties
    FROM canonical_nodes v
    JOIN project_relations e ON e.to_node = v.id
    WHERE e.from_node = %s AND v.key LIKE 'prop:%%'
    ORDER BY v.name
    """
    return db.execute(query, (class_id,)).fetchall()

def get_class_methods(class_id: int) -> list:
    """Получить методы класса"""
    query = """
    SELECT v.id, v.key, v.name, v.properties
    FROM canonical_nodes v
    JOIN project_relations e ON e.to_node = v.id
    WHERE e.from_node = %s AND v.key LIKE 'meth:%%'
    ORDER BY v.name
    """
    return db.execute(query, (class_id,)).fetchall()

def get_class_relations(class_id: int) -> list:
    """Получить связи класса"""
    query = """
    SELECT v.id, v.key, v.name, v.properties
    FROM canonical_nodes v
    JOIN project_relations e ON e.to_node = v.id
    WHERE e.from_node = %s AND v.key LIKE 'rel:%%'
    ORDER BY v.name
    """
    return db.execute(query, (class_id,)).fetchall()
```

---

## MCP команды для работы с классами

### Новые команды

**Файл**: `src/mcp_server/handlers/class_operations.py`

```python
@mcp_tool()
def class_create(
    class_key: str,
    class_name: str,
    extends: Optional[str] = None,
    abstract: bool = False,
    backend_module: Optional[str] = None,
    frontend_module: Optional[str] = None,
    description: str = ''
) -> dict:
    """
    Создать определение класса в графе
    
    Args:
        class_key: Ключ класса (например 'cls:Project')
        class_name: Название класса
        extends: Родительский класс (ключ, например 'cls:ConceptVertex')
        abstract: Является ли класс абстрактным
        backend_module: Путь к модулю на бакенде (например 'models.business.project')
        frontend_module: Путь к модулю на фронтенде (например 'models/business/Project.js')
        description: Описание класса
    
    Returns:
        {"status": "success", "class_id": "..."}
    """

@mcp_tool()
def class_add_property(
    class_key: str,
    property_name: str,
    property_type: str,
    required: bool = False,
    default: Optional[Any] = None,
    pattern: Optional[str] = None,
    description: str = ''
) -> dict:
    """Добавить свойство к классу"""

@mcp_tool()
def class_add_method(
    class_key: str,
    method_name: str,
    returns: str,
    params: Optional[Dict[str, str]] = None,
    description: str = '',
    lazy: bool = False
) -> dict:
    """Добавить метод к классу"""

@mcp_tool()
def class_add_relation(
    class_key: str,
    relation_name: str,
    relation_type: str,  # one_to_many, many_to_one, many_to_many
    target_class: str,
    edge_type: str = 'related',
    description: str = ''
) -> dict:
    """Добавить связь между классами"""

@mcp_tool()
def class_regenerate_code(class_key: Optional[str] = None) -> dict:
    """
    Регенерировать код классов из графа
    
    Args:
        class_key: Ключ конкретного класса (если None - все классы)
    
    Returns:
        {"status": "success", "generated_files": [...]}
    """
```

---

## Генератор кода из графа

### Основной скрипт

**Файл**: `tools/generate_from_graph.py`

Читает метаданные из графа и генерирует классы для Python и JavaScript.

**Использование**:
```bash
# Генерация всех классов
python tools/generate_from_graph.py

# Генерация конкретного класса
python tools/generate_from_graph.py --class cls:Project

# Только бакенд
python tools/generate_from_graph.py --backend-only

# Только фронтенд
python tools/generate_from_graph.py --frontend-only
```

### Шаблоны

**`tools/templates/python_class.jinja2`** — шаблон для Python классов
**`tools/templates/js_class.jinja2`** — шаблон для JavaScript классов

---

## Обновление .cursorrules

```markdown
## 🔴 КРИТИЧЕСКИ ВАЖНО: Контекст проекта

### В начале КАЖДОГО чата выполнить:
```
graph_traverse_down(project="fedoc", include_metadata=true)
```

**Что включает вывод с `include_metadata=true`**:
1. **Структура проекта**: Иерархия компонентов и технологий
2. **Метаданные классов**: Определения всех классов (базовых и бизнес)
3. **Конфигурация визуализации**: Стили узлов, рёбер, layout, physics
4. **API контракт**: Описание всех эндпоинтов

**Почему это важно**:
- Граф — единственный источник истины о проекте И его архитектуре
- AI получает актуальные определения классов при каждом запуске
- Изменения в схеме немедленно видны всем инструментам
- Нет разночтений между документацией и реальностью
- На клиенте хранятся только секреты, вся логика в графе
```

---

## Преимущества архитектуры

✅ **Единственный источник истины**: Граф (не YAML, не JSON)  
✅ **AI всегда актуален**: Метаданные в начале каждого чата  
✅ **Версионирование**: История изменений классов в графе  
✅ **Нет дублирования**: Никаких конфигурационных файлов  
✅ **Автоматическая синхронизация**: Генераторы читают граф  
✅ **Визуализация**: Классы видны в Graph Viewer  
✅ **MCP интеграция**: AI может изменять схему командами  
✅ **Философия fedoc**: Всё в графе, на клиенте только секреты  
✅ **Масштабируемость**: Легко добавлять новые классы  
✅ **Консистентность**: Фронтенд и бакенд используют одну схему

---

## Следующие шаги

1. Создать базовую структуру метаузлов в графе
2. Реализовать расширенную версию `graph_traverse_down`
3. Реализовать генератор кода `tools/generate_from_graph.py`
4. Создать MCP команды для работы с классами
5. Протестировать полный цикл: граф → генерация → использование
6. Обновить `.cursorrules`

---

**Дата создания**: 2025-11-04  
**Автор**: Александр  
**Версия**: 1.0

