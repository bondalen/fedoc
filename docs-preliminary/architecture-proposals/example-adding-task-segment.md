# Пример: Добавление сегмента "Задачи" и типа "Задача"

**Дата**: 2025-11-05  
**Статус**: Пример использования

---

## Задача

Добавить новый сегмент графа "Задачи" с типом вершин "Задача" для отслеживания задач проекта.

---

## Шаг 1: Создание классов

### 1.1. Создать класс сегмента

```python
# models/segments/task_segment.py
from models.vertices.graph_vertex import GraphVertex

class TaskSegmentVertex(GraphVertex):
    """Сегмент задач проекта"""
    SEGMENT_NAME = 'tasks'
    
    @classmethod
    def get_segment_nodes(cls):
        """Получить все типы узлов сегмента"""
        return ['task']
```

### 1.2. Создать класс типа вершины

```python
# models/vertices/task_vertex.py
from models.segments.task_segment import TaskSegmentVertex

class TaskVertex(TaskSegmentVertex):
    """Вершина задачи"""
    KEY_PREFIX = 'task:'
    NODE_TYPE = 'task'
    
    def __init__(self, key, name, **kwargs):
        if not key.startswith(self.KEY_PREFIX):
            raise ValueError(f"Task key must start with {self.KEY_PREFIX}")
        super().__init__(key, name, node_type=self.NODE_TYPE, **kwargs)
    
    def get_visual_style(self, theme='light'):
        """Специфичный стиль для задач"""
        return {
            'shape': 'box',
            'color': '#FF6F00',
            'border': '#E65100',
            'size': {'width': 150, 'height': 40}
        }
```

---

## Шаг 2: Регистрация типа в реестре

### 2.1. Через MCP команду

```python
# Вызов MCP команды
vertex_type_register(
    type_name="task",
    key_prefix="task:",
    segment="tasks",
    base_class="TaskVertex",
    validation_pattern="^task:.+",
    visual_style={
        "shape": "box",
        "color": "#FF6F00",
        "border": "#E65100",
        "size": {
            "width": 150,
            "height": 40
        }
    }
)
```

### 2.2. Что происходит внутри

```python
# models/vertex_type_registry.py
def register_type(self, type_name, key_prefix, segment, 
                 base_class, validation_pattern, visual_style):
    """Зарегистрировать новый тип"""
    
    # 1. Сохранить в память
    self._types[type_name] = {
        'key_prefix': key_prefix,
        'segment': segment,
        'base_class': base_class,
        'validation_pattern': validation_pattern,
        'visual_style': visual_style
    }
    
    # 2. Сохранить в граф
    type_key = f"c:vertex-type-{type_name}"
    create_node(
        node_key=type_key,
        node_name=f"Тип вершины: {type_name}",
        node_type="concept",
        properties={
            'type_name': type_name,
            'key_prefix': key_prefix,
            'segment': segment,
            'base_class': base_class,
            'validation_pattern': validation_pattern,
            'visual_style': visual_style
        }
    )
    
    # 3. Связать с реестром
    create_edge(
        from_node="c:vertex-types-registry",
        to_node=type_key,
        edge_type="contains"
    )
```

---

## Шаг 3: Использование

### 3.1. Создание задачи через API

```python
# POST /api/nodes
{
    "node_key": "task:implement-registry",
    "node_name": "Реализовать реестр типов вершин",
    "node_type": "task",
    "properties": {
        "status": "in_progress",
        "priority": "high",
        "assignee": "alex"
    }
}
```

### 3.2. Валидация через реестр

```python
# api_server_age.py
@app.route('/api/nodes', methods=['POST'])
def create_node():
    node_type = data.get('node_type')
    
    # Проверка через реестр
    if node_type not in vertex_type_registry.get_all_types():
        return jsonify({'error': 'Некорректный тип узла'}), 400
    
    # Валидация ключа через реестр
    if not vertex_type_registry.validate_key(node_key, node_type):
        expected_prefix = vertex_type_registry.get_expected_prefix(node_type)
        return jsonify({'error': f'Ожидается префикс: {expected_prefix}'}), 400
    
    # Создание через фабрику
    vertex = vertex_factory.create_vertex(
        node_key=node_key,
        node_name=node_name,
        node_type=node_type,
        properties=properties
    )
```

### 3.3. Создание через фабрику

```python
# models/vertex_factory.py
class VertexFactory:
    def create_vertex(self, node_key, node_name, node_type, properties):
        """Создать вершину на основе типа"""
        
        # Получить метаданные типа из реестра
        type_info = vertex_type_registry.get_type(node_type)
        if not type_info:
            raise ValueError(f"Unknown vertex type: {type_type}")
        
        # Получить класс для создания
        base_class_name = type_info['base_class']
        vertex_class = self._get_class_by_name(base_class_name)
        
        # Создать экземпляр
        return vertex_class(
            key=node_key,
            name=node_name,
            **properties
        )
    
    def _get_class_by_name(self, class_name):
        """Получить класс по имени"""
        # Маппинг имён классов на классы
        class_map = {
            'TaskVertex': TaskVertex,
            'ConceptVertex': ConceptVertex,
            # ...
        }
        return class_map.get(class_name, OtherVertex)
```

---

## Шаг 4: Визуализация на фронтенде

### 4.1. Загрузка типов из API

```javascript
// stores/vertexTypes.js
export async function loadVertexTypes() {
  const response = await fetch('/api/vertex-types')
  const types = await response.json()
  
  // types теперь содержит:
  // {
  //   "task": {
  //     "key_prefix": "task:",
  //     "segment": "tasks",
  //     "visual_style": {...}
  //   },
  //   ...
  // }
  
  Object.assign(vertexTypes, types)
}
```

### 4.2. Определение типа по ключу

```javascript
// utils/segments.js
export function getNodeType(nodeKey) {
  if (!nodeKey) return 'default'
  
  // Проверить все зарегистрированные типы
  for (const [typeName, typeInfo] of Object.entries(vertexTypes)) {
    if (nodeKey.startsWith(typeInfo.key_prefix)) {
      return typeName
    }
  }
  
  return 'default'
}

// Использование
getNodeType("task:implement-registry") // → "task"
```

### 4.3. Применение стилей

```javascript
// utils/visualization.js
export function applyNodeVisualization(node, theme) {
  const nodeType = getNodeType(node.key)
  const typeInfo = vertexTypes[nodeType]
  
  if (typeInfo && typeInfo.visual_style) {
    // Применить стиль из метаданных
    const style = typeInfo.visual_style[theme] || typeInfo.visual_style.light
    return {
      ...node,
      shape: style.shape,
      color: style.color,
      // ...
    }
  }
  
  // Fallback на дефолтный стиль
  return applyDefaultStyle(node, theme)
}
```

---

## Шаг 5: Фильтрация по сегменту

### 5.1. API endpoint

```python
@app.route('/api/graph', methods=['GET'])
def get_graph():
    segments = request.args.get('segments', '').split(',')
    
    if 'tasks' in segments:
        # Включить узлы типа "task"
        node_types.extend(['task'])
```

### 5.2. На фронтенде

```vue
<!-- components/SegmentFilter.vue -->
<template>
  <div class="segment-filter">
    <label>
      <input type="checkbox" v-model="selectedSegments" value="architecture" />
      Архитектура
    </label>
    <label>
      <input type="checkbox" v-model="selectedSegments" value="code_structure" />
      Структура кода
    </label>
    <label>
      <input type="checkbox" v-model="selectedSegments" value="filesystem" />
      Файловая система
    </label>
    <label>
      <input type="checkbox" v-model="selectedSegments" value="tasks" />
      Задачи
    </label>
  </div>
</template>
```

---

## Результат

После выполнения всех шагов:

✅ **Новый сегмент "Задачи"** добавлен в систему  
✅ **Тип "task"** зарегистрирован в реестре  
✅ **Класс TaskVertex** создан и работает  
✅ **Валидация** работает автоматически  
✅ **Визуализация** применяется из метаданных  
✅ **Фильтрация** по сегменту работает  
✅ **Не требуется** перезапуск сервера (если используется динамическая загрузка)  

---

## Структура в графе

```
c:vertex-types-registry
  ├─→ c:vertex-type-concept
  ├─→ c:vertex-type-technology
  ├─→ c:vertex-type-version
  ├─→ c:vertex-type-module
  ├─→ c:vertex-type-component
  ├─→ c:vertex-type-class
  ├─→ c:vertex-type-nested-class
  ├─→ c:vertex-type-directory
  ├─→ c:vertex-type-file
  └─→ c:vertex-type-task  ← новый тип
```

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

