# Синхронизация классов между фронтендом и бакендом

**Дата**: 2025-11-04  
**Статус**: Предложение (промежуточное)  
**Заменено на**: Метаданные в графе (см. `metadata-in-graph-architecture.md`)

---

## Историческая справка

Это предложение было промежуточным этапом в развитии архитектуры. 

**Исходная идея**: Использовать YAML файл `config/schema/graph-schema.yaml` как единый источник правды и генерировать из него классы для Python и JavaScript.

**Проблема**: Дублирование источников истины (граф + YAML).

**Финальное решение**: Хранить метаданные классов в самом графе (философия fedoc).

Документ сохранён для истории и понимания эволюции архитектуры.

---

## Концепция с YAML (устаревшая)

### Единая схема данных

**Файл**: `config/schema/graph-schema.yaml`

```yaml
# Базовые типы
base_types:
  GraphObject:
    description: "Базовый класс для всех объектов графа"
    properties:
      id: 
        type: string
        required: true
      created_at: 
        type: datetime
      updated_at: 
        type: datetime
    methods:
      - to_dict
      - from_dict
      - validate

# Вершины
vertices:
  GraphVertex:
    extends: GraphObject
    abstract: true
    properties:
      key:
        type: string
        required: true
        pattern: "^[ctv]:.+"
      label:
        type: string
        required: true
      node_type:
        type: enum
        values: [concept, technology, version, default]
    methods:
      - infer_type
      - get_visual_style
      - to_vis_format
      - to_svg_format
  
  ConceptVertex:
    extends: GraphVertex
    node_type: concept
    key_prefix: "c:"
    visualization:
      dark:
        color: "#1976D2"
        border: "#0D47A1"
        shape: box
      light:
        color: "#E3F2FD"
        border: "#90CAF9"
        shape: box

# Бизнес-сущности
business_entities:
  Project:
    extends: ConceptVertex
    key_pattern: "^c:project$"
    properties:
      name: string
      description: string
      repository_url: url
    relations:
      has_backend: 
        type: one_to_many
        target: Backend
      uses_technologies:
        type: many_to_many
        target: TechnologyVertex
  
  Backend:
    extends: ConceptVertex
    key_pattern: "^c:backend.*"
    properties:
      framework: string
      database: string
      api_type: 
        type: enum
        values: [REST, GraphQL, gRPC]
    relations:
      belongs_to_project:
        type: many_to_one
        target: Project
```

---

## Структура классов на бакенде (Python)

```
src/lib/graph_viewer/backend/
├── models/
│   ├── __init__.py
│   ├── base.py                      # GraphObject
│   ├── vertices/
│   │   ├── __init__.py
│   │   ├── graph_vertex.py         # GraphVertex (абстрактный)
│   │   ├── concept_vertex.py       # ConceptVertex
│   │   ├── technology_vertex.py    # TechnologyVertex
│   │   └── version_vertex.py       # VersionVertex
│   ├── edges/
│   │   ├── __init__.py
│   │   └── graph_edge.py           # GraphEdge
│   └── business/
│       ├── __init__.py
│       ├── project.py              # Project
│       ├── backend.py              # Backend
│       └── frontend.py             # Frontend
├── services/
│   ├── graph_service.py            # Бизнес-логика графа
│   └── serialization_service.py    # Сериализация
└── repositories/
    ├── vertex_repository.py
    └── edge_repository.py
```

---

## Структура классов на фронтенде (JavaScript)

```
src/lib/graph_viewer/frontend/src/
├── models/
│   ├── base.js                      # GraphObject
│   ├── vertices/
│   │   ├── GraphVertex.js
│   │   ├── ConceptVertex.js
│   │   ├── TechnologyVertex.js
│   │   └── VersionVertex.js
│   ├── edges/
│   │   └── GraphEdge.js
│   └── business/
│       ├── Project.js
│       ├── Backend.js
│       └── Frontend.js
└── services/
    ├── VisualizationManager.js
    └── GraphRepository.js
```

---

## Генератор классов из YAML

**Файл**: `tools/generate_classes.py`

```python
#!/usr/bin/env python3
"""
Генерация классов из YAML схемы
"""
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def load_schema(schema_path):
    with open(schema_path) as f:
        return yaml.safe_load(f)

def generate_python_classes(schema, output_dir):
    """Генерировать Python классы"""
    env = Environment(loader=FileSystemLoader('tools/templates'))
    template = env.get_template('python_class.jinja2')
    
    for entity_name, entity_def in schema['business_entities'].items():
        # Определить путь к файлу
        module_name = entity_name.lower()
        file_path = output_dir / 'business' / f"{module_name}.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Сгенерировать код
        code = template.render(
            class_name=entity_name,
            entity_def=entity_def,
            schema=schema
        )
        
        file_path.write_text(code)
        print(f"✅ Generated: {file_path}")

def generate_javascript_classes(schema, output_dir):
    """Генерировать JavaScript классы"""
    env = Environment(loader=FileSystemLoader('tools/templates'))
    template = env.get_template('js_class.jinja2')
    
    for entity_name, entity_def in schema['business_entities'].items():
        # Определить путь к файлу
        file_path = output_dir / 'business' / f"{entity_name}.js"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Сгенерировать код
        code = template.render(
            class_name=entity_name,
            entity_def=entity_def,
            schema=schema
        )
        
        file_path.write_text(code)
        print(f"✅ Generated: {file_path}")

if __name__ == '__main__':
    schema = load_schema('config/schema/graph-schema.yaml')
    
    backend_path = Path('src/lib/graph_viewer/backend/models')
    frontend_path = Path('src/lib/graph_viewer/frontend/src/models')
    
    generate_python_classes(schema, backend_path)
    generate_javascript_classes(schema, frontend_path)
```

**Использование**:
```bash
python tools/generate_classes.py --schema config/schema/graph-schema.yaml \
  --python-output src/lib/graph_viewer/backend/models/ \
  --js-output src/lib/graph_viewer/frontend/src/models/
```

---

## Проверка синхронности

**Файл**: `tools/sync_check.py`

```python
#!/usr/bin/env python3
"""
Проверка синхронности классов между фронтендом и бакендом
"""
import yaml
from pathlib import Path

def check_backend_models(schema, backend_path):
    """Проверить наличие всех классов на бакенде"""
    errors = []
    
    for entity_name, entity_def in schema['business_entities'].items():
        model_file = backend_path / f"{entity_name.lower()}.py"
        if not model_file.exists():
            errors.append(f"Missing backend model: {entity_name}")
        else:
            # Проверить методы
            with open(model_file) as f:
                content = f.read()
                for method in entity_def.get('methods', []):
                    if f"def {method}" not in content:
                        errors.append(
                            f"Missing method {method} in backend {entity_name}"
                        )
    
    return errors

def check_frontend_models(schema, frontend_path):
    """Проверить наличие всех классов на фронтенде"""
    errors = []
    
    for entity_name, entity_def in schema['business_entities'].items():
        model_file = frontend_path / f"{entity_name}.js"
        if not model_file.exists():
            errors.append(f"Missing frontend model: {entity_name}")
    
    return errors

if __name__ == '__main__':
    schema = yaml.safe_load(open('config/schema/graph-schema.yaml'))
    
    backend_path = Path('src/lib/graph_viewer/backend/models/business')
    frontend_path = Path('src/lib/graph_viewer/frontend/src/models/business')
    
    errors = []
    errors.extend(check_backend_models(schema, backend_path))
    errors.extend(check_frontend_models(schema, frontend_path))
    
    if errors:
        print("❌ Sync check failed:")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("✅ All models are synchronized")
```

---

## Почему подход с YAML был отклонён

### Проблемы:

1. **Дублирование источников истины**
   - Граф хранит данные
   - YAML хранит схему
   - Риск рассинхронизации

2. **Не соответствует философии fedoc**
   - Цель: всё в графе
   - На клиенте только секреты
   - YAML — это конфигурационный файл на клиенте

3. **Версионирование**
   - YAML файл в Git
   - Изменения схемы через коммиты
   - Граф не участвует в версионировании схемы

4. **AI интеграция**
   - AI читает граф через `graph_traverse_down`
   - YAML файл нужно читать отдельно
   - Дополнительная команда MCP

---

## Финальное решение: Метаданные в графе

См. [`metadata-in-graph-architecture.md`](./metadata-in-graph-architecture.md)

**Ключевые отличия**:

| Аспект | YAML подход | Граф подход |
|--------|-------------|-------------|
| Источник правды | YAML файл | Граф |
| AI доступ | Отдельная команда | `graph_traverse_down` |
| Версионирование | Git (YAML) | Граф (история изменений) |
| Изменение схемы | Редактировать YAML | MCP команды |
| Визуализация | Нет | Graph Viewer |
| Философия fedoc | ❌ Файл на клиенте | ✅ Всё в графе |

---

## Преимущества финального решения

✅ **Единственный источник правды**: Граф  
✅ **AI всегда актуален**: Получает из графа при каждом запуске  
✅ **Версионирование в графе**: История изменений  
✅ **Нет конфиг файлов**: На клиенте только секреты  
✅ **MCP интеграция**: AI может менять схему  
✅ **Визуализация**: Классы видны в Graph Viewer  
✅ **Философия fedoc**: 100% соответствие

---

## Миграционный путь

Если бы мы начали с YAML подхода, миграция в граф:

1. Прочитать YAML файл
2. Создать метаузлы в графе для каждого класса
3. Перенести свойства, методы, связи
4. Обновить `graph_traverse_down` для чтения из графа
5. Обновить генератор для чтения из графа
6. Удалить YAML файл
7. Обновить `.cursorrules`

---

**Дата создания**: 2025-11-04  
**Автор**: Александр  
**Статус**: Архивный (заменён на metadata-in-graph-architecture.md)
