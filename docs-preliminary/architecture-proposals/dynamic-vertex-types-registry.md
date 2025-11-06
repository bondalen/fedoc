# Механизм оперативного добавления типов вершин

**Дата**: 2025-11-05  
**Статус**: Предложение  
**Приоритет**: Высокий

---

## Проблема

Текущая реализация использует жёстко заданные типы вершин в коде:
- Список типов в `valid_types = ['concept', 'technology', 'version', ...]`
- Функции валидации `validate_node_key()` с if/elif цепочками
- Функции определения типа `get_expected_prefix()` со словарём

**Недостатки**:
- ❌ Добавление нового типа требует изменения кода
- ❌ Нужно обновлять несколько мест (бакенд, фронтенд, валидация)
- ❌ Нет единого источника истины о типах
- ❌ Сложно расширять систему

---

## Решение: Регистрация типов вершин

### Подход 1: Метаданные в графе (рекомендуется)

**Философия fedoc**: Всё в графе, включая метаданные типов вершин.

#### Структура в графе

```
c:meta
  c:vertex-types-registry (Реестр типов вершин)
    
    # Типы архитектуры
    c:vertex-type-concept
      properties: {
        type_name: "concept",
        key_prefix: "c:",
        segment: "architecture",
        base_class: "ConceptVertex",
        validation_pattern: "^c:.+",
        visual_style: {
          shape: "box",
          color: "#1976D2"
        }
      }
    
    c:vertex-type-technology
      properties: {
        type_name: "technology",
        key_prefix: "t:",
        segment: "architecture",
        base_class: "TechnologyVertex",
        validation_pattern: "^t:.+",
        visual_style: {
          shape: "circle",
          color: "#388E3C"
        }
      }
    
    # Новый тип можно добавить через MCP команду
    c:vertex-type-custom
      properties: {
        type_name: "custom",
        key_prefix: "custom:",
        segment: "other",
        base_class: "OtherVertex",
        validation_pattern: "^custom:.+",
        visual_style: {
          shape: "diamond",
          color: "#9B59B6"
        }
      }
```

#### Реализация

**Бакенд: Реестр типов вершин**

```python
# models/vertex_type_registry.py
class VertexTypeRegistry:
    """Реестр типов вершин, загружаемый из графа"""
    
    def __init__(self):
        self._types = {}
        self._load_from_graph()
    
    def _load_from_graph(self):
        """Загрузить типы вершин из графа"""
        query = """
        MATCH (registry:ConceptVertex {key: 'c:vertex-types-registry'})
        MATCH (registry)-[:contains]->(type:ConceptVertex)
        WHERE type.key STARTS WITH 'c:vertex-type-'
        RETURN type
        """
        
        types = db.execute(query)
        for type_node in types:
            props = type_node.properties
            self._types[props['type_name']] = {
                'key_prefix': props['key_prefix'],
                'segment': props['segment'],
                'base_class': props['base_class'],
                'validation_pattern': props['validation_pattern'],
                'visual_style': props['visual_style']
            }
    
    def get_type(self, type_name: str) -> dict:
        """Получить метаданные типа"""
        return self._types.get(type_name)
    
    def validate_key(self, node_key: str, node_type: str) -> bool:
        """Валидация ключа узла"""
        type_info = self.get_type(node_type)
        if not type_info:
            return False
        
        import re
        pattern = type_info['validation_pattern']
        return bool(re.match(pattern, node_key))
    
    def get_expected_prefix(self, node_type: str) -> str:
        """Получить ожидаемый префикс для типа"""
        type_info = self.get_type(node_type)
        return type_info['key_prefix'] if type_info else 'неизвестный'
    
    def get_segment(self, node_type: str) -> str:
        """Получить сегмент для типа"""
        type_info = self.get_type(node_type)
        return type_info['segment'] if type_info else 'other'
    
    def get_all_types(self) -> list:
        """Получить все зарегистрированные типы"""
        return list(self._types.keys())
    
    def register_type(self, type_name: str, key_prefix: str, 
                     segment: str, base_class: str, 
                     validation_pattern: str, visual_style: dict):
        """Зарегистрировать новый тип (динамически)"""
        self._types[type_name] = {
            'key_prefix': key_prefix,
            'segment': segment,
            'base_class': base_class,
            'validation_pattern': validation_pattern,
            'visual_style': visual_style
        }
        
        # Сохранить в граф
        self._save_to_graph(type_name, key_prefix, segment, 
                           base_class, validation_pattern, visual_style)
    
    def _save_to_graph(self, type_name: str, key_prefix: str, 
                      segment: str, base_class: str,
                      validation_pattern: str, visual_style: dict):
        """Сохранить тип в граф"""
        type_key = f"c:vertex-type-{type_name}"
        
        # Создать узел типа в графе
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
        
        # Связать с реестром
        create_edge(
            from_node="c:vertex-types-registry",
            to_node=type_key,
            edge_type="contains"
        )

# Глобальный экземпляр реестра
vertex_type_registry = VertexTypeRegistry()
```

**Использование в API**

```python
# api_server_age.py
from models.vertex_type_registry import vertex_type_registry

@app.route('/api/nodes', methods=['POST'])
def create_node():
    node_type = data.get('node_type')
    
    # Валидация через реестр
    if node_type not in vertex_type_registry.get_all_types():
        return jsonify({'error': f'Некорректный тип узла. Допустимые: {", ".join(vertex_type_registry.get_all_types())}'}), 400
    
    # Валидация ключа через реестр
    if not vertex_type_registry.validate_key(node_key, node_type):
        expected_prefix = vertex_type_registry.get_expected_prefix(node_type)
        return jsonify({'error': f'Некорректный формат ключа. Ожидается префикс: {expected_prefix}'}), 400
```

**MCP команда для регистрации типа**

```python
@mcp_tool()
def vertex_type_register(
    type_name: str,
    key_prefix: str,
    segment: str,  # architecture, code_structure, filesystem, other
    base_class: str,  # ConceptVertex, TechnologyVertex, etc.
    validation_pattern: str,
    visual_style: dict
) -> dict:
    """
    Зарегистрировать новый тип вершины в системе
    
    Args:
        type_name: Название типа (например, 'custom')
        key_prefix: Префикс ключа (например, 'custom:')
        segment: Сегмент графа (architecture, code_structure, filesystem, other)
        base_class: Базовый класс (ConceptVertex, TechnologyVertex, etc.)
        validation_pattern: Регулярное выражение для валидации ключа
        visual_style: Стиль визуализации {shape, color, size}
    
    Returns:
        {"status": "success", "type_name": "..."}
    """
    vertex_type_registry.register_type(
        type_name=type_name,
        key_prefix=key_prefix,
        segment=segment,
        base_class=base_class,
        validation_pattern=validation_pattern,
        visual_style=visual_style
    )
    
    return {"status": "success", "type_name": type_name}
```

---

### Подход 2: Конфигурационный файл (альтернатива)

Если метаданные в графе слишком сложны для MVP, можно использовать YAML/JSON конфигурацию.

**Файл**: `config/vertex_types.yaml`

```yaml
vertex_types:
  concept:
    key_prefix: "c:"
    segment: "architecture"
    base_class: "ConceptVertex"
    validation_pattern: "^c:.+"
    visual_style:
      shape: "box"
      color: "#1976D2"
  
  technology:
    key_prefix: "t:"
    segment: "architecture"
    base_class: "TechnologyVertex"
    validation_pattern: "^t:.+"
    visual_style:
      shape: "circle"
      color: "#388E3C"
  
  custom:
    key_prefix: "custom:"
    segment: "other"
    base_class: "OtherVertex"
    validation_pattern: "^custom:.+"
    visual_style:
      shape: "diamond"
      color: "#9B59B6"
```

**Загрузка конфигурации**

```python
# models/vertex_type_registry.py
import yaml
from pathlib import Path

class VertexTypeRegistry:
    def __init__(self, config_path: str = "config/vertex_types.yaml"):
        self._types = {}
        self._load_from_config(config_path)
    
    def _load_from_config(self, config_path: str):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            self._types = config.get('vertex_types', {})
```

---

### Подход 3: Гибридный (рекомендуется для MVP)

1. **Базовые типы** — в коде (для производительности)
2. **Расширенные типы** — в графе (для гибкости)

```python
class VertexTypeRegistry:
    # Базовые типы (жёстко заданы)
    BASE_TYPES = {
        'concept': {'key_prefix': 'c:', 'segment': 'architecture', ...},
        'technology': {'key_prefix': 't:', 'segment': 'architecture', ...},
        # ...
    }
    
    def __init__(self):
        self._types = self.BASE_TYPES.copy()
        self._load_extended_types_from_graph()
    
    def _load_extended_types_from_graph(self):
        """Загрузить расширенные типы из графа"""
        # Загрузить только типы, которых нет в BASE_TYPES
        pass
```

---

## Фронтенд: Динамическая загрузка типов

```javascript
// stores/vertexTypes.js
import { ref, reactive } from 'vue'

export const vertexTypes = reactive({})

export async function loadVertexTypes() {
  const response = await fetch('/api/vertex-types')
  const types = await response.json()
  
  Object.assign(vertexTypes, types)
}

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

export function getVisualStyle(nodeType, theme = 'light') {
  const typeInfo = vertexTypes[nodeType]
  if (!typeInfo) return getDefaultStyle(theme)
  
  return typeInfo.visual_style[theme] || typeInfo.visual_style.light
}
```

**API endpoint для фронтенда**

```python
@app.route('/api/vertex-types', methods=['GET'])
def get_vertex_types():
    """Получить все зарегистрированные типы вершин"""
    types = {}
    for type_name, type_info in vertex_type_registry.get_all_types_with_info().items():
        types[type_name] = {
            'key_prefix': type_info['key_prefix'],
            'segment': type_info['segment'],
            'visual_style': type_info['visual_style']
        }
    return jsonify(types)
```

---

## Преимущества подхода

✅ **Единый источник истины**: Типы в графе (или конфиге)  
✅ **Оперативное добавление**: Через MCP команду без изменения кода  
✅ **Автоматическая синхронизация**: Фронтенд загружает типы из API  
✅ **Визуализация**: Стили хранятся вместе с типами  
✅ **Валидация**: Паттерны валидации в метаданных  
✅ **Расширяемость**: Легко добавить новые типы  

---

## Пример использования

### Добавление нового типа "test"

```python
# Через MCP команду
vertex_type_register(
    type_name="test",
    key_prefix="test:",
    segment="other",
    base_class="OtherVertex",
    validation_pattern="^test:.+",
    visual_style={
        "shape": "hexagon",
        "color": "#FF6F00",
        "size": {"width": 100, "height": 50}
    }
)
```

После этого:
- ✅ Тип автоматически доступен в API
- ✅ Валидация работает автоматически
- ✅ Фронтенд получает стили через `/api/vertex-types`
- ✅ Не нужно перезапускать сервер (если используется динамическая загрузка)

---

## Следующие шаги

1. Реализовать `VertexTypeRegistry` с загрузкой из графа
2. Создать MCP команду `vertex_type_register`
3. Обновить API для использования реестра
4. Обновить фронтенд для динамической загрузки типов
5. Мигрировать существующие типы в граф

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

