# Подход: Тип вершины в ключе узла

**Дата**: 2025-11-05  
**Статус**: Предложение (радикальное упрощение)  
**Приоритет**: Высокий

---

## Концепция

Вместо отдельного поля `node_type` использовать префикс ключа узла как тип вершины.

**Формат**: `{segment}.{type}.{identifier}`

---

## Структура ключей

### Формат: `{segment}.{type}.{identifier}`

**Примеры**:
- `a.c.project` — архитектура:концепт:проект
- `a.c.backend` — архитектура:концепт:бакенд
- `a.t.python` — архитектура:технология:python
- `a.t.vue` — архитектура:технология:vue
- `a.v.python@3.12` — архитектура:версия:python@3.12
- `c.m.lib.graph_viewer` — код:модуль:lib.graph_viewer
- `c.comp.api_server_age` — код:компонент:api_server_age
- `c.class.GraphObject` — код:класс:GraphObject
- `c.nested.GraphObject.Validator` — код:вложенный_класс:GraphObject.Validator
- `f.d.src/lib/graph_viewer` — файловая_система:директория:src/lib/graph_viewer
- `f.file.api_server.py` — файловая_система:файл:api_server.py
- `o.custom` — прочие:custom

### Сегменты (segment)
- `a` — architecture (архитектура)
- `c` — code_structure (структура кода)
- `f` — filesystem (файловая система)
- `o` — other (прочие)

### Типы (type)
- **Архитектура**: `c` (concept), `t` (technology), `v` (version)
- **Код**: `m` (module), `comp` (component), `class`, `nested`
- **Файловая система**: `d` (directory), `file`
- **Прочие**: любой

---

## Преимущества

✅ **Единый источник истины**: Тип закодирован в ключе  
✅ **Нет дублирования**: Не нужно хранить `node_type` отдельно  
✅ **Простота**: Не нужно валидировать соответствие ключа и типа  
✅ **Самодокументируемость**: По ключу сразу понятен тип  
✅ **Упрощённая визуализация**: Парсинг ключа → получение стиля  

---

## Проблемы и решения

### 1. Миграция существующих данных

**Проблема**: Существующие ключи `c:project`, `t:python` нужно мигрировать в `a.c.project`, `a.t.python`.

**Решение**: Создать функцию миграции:

```python
# migrations/migrate_keys_to_type_in_key.py
def migrate_node_key(old_key: str, node_type: str) -> str:
    """
    Мигрировать ключ из старого формата в новый
    
    Старый: c:project, t:python
    Новый: a.c.project, a.t.python
    """
    # Маппинг старого типа на новый сегмент и тип
    type_mapping = {
        'concept': ('a', 'c'),
        'technology': ('a', 't'),
        'version': ('a', 'v'),
        'module': ('c', 'm'),
        'component': ('c', 'comp'),
        'class': ('c', 'class'),
        'nested-class': ('c', 'nested'),
        'directory': ('f', 'd'),
        'file': ('f', 'file'),
        'other': ('o', 'other')
    }
    
    segment, type_part = type_mapping.get(node_type, ('o', 'other'))
    
    # Извлечь идентификатор из старого ключа
    if ':' in old_key:
        identifier = old_key.split(':', 1)[1]
    else:
        identifier = old_key
    
    # Сформировать новый ключ
    return f"{segment}.{type_part}.{identifier}"

# SQL миграция
UPDATE canonical_nodes
SET arango_key = migrate_key(arango_key, node_type)
WHERE arango_key LIKE '%:%';
```

### 2. Обратная совместимость

**Проблема**: Существующий код ожидает ключи в формате `c:project`.

**Решение**: Поддержка обоих форматов в переходный период:

```python
def normalize_node_key(key: str) -> tuple[str, str]:
    """
    Нормализовать ключ узла и извлечь тип
    
    Returns:
        (normalized_key, type_key_for_style)
    """
    # Новый формат: a.c.project
    if '.' in key and not key.startswith('c:') and not key.startswith('t:'):
        parts = key.split('.', 2)
        if len(parts) >= 2:
            segment, type_part = parts[0], parts[1]
            return key, f"{segment}.{type_part}"
    
    # Старый формат: c:project
    if ':' in key:
        prefix, identifier = key.split(':', 1)
        # Маппинг префикса на новый формат
        prefix_mapping = {
            'c': 'a.c',
            't': 'a.t',
            'v': 'a.v',
            'm': 'c.m',
            'comp': 'c.comp',
            'd': 'f.d',
            'f': 'f.file'
        }
        new_prefix = prefix_mapping.get(prefix, 'o.other')
        new_key = f"{new_prefix}.{identifier}"
        return new_key, new_prefix
    
    # Неизвестный формат
    return key, 'o.other'
```

### 3. Поиск узлов по ключу

**Проблема**: Запросы к БД используют `arango_key` для поиска.

**Решение**: Поиск работает с любым форматом:

```python
def find_node_by_key(key: str):
    """Найти узел по ключу (поддержка обоих форматов)"""
    normalized_key, _ = normalize_node_key(key)
    
    query = f"""
        MATCH (n {{arango_key: '{normalized_key}'}})
        RETURN n
    """
    # Или поиск по обоим форматам
    query = f"""
        MATCH (n)
        WHERE n.arango_key = '{normalized_key}' 
           OR n.arango_key = '{key}'  -- старый формат
        RETURN n
    """
```

### 4. Длинные ключи

**Проблема**: Ключи могут стать длинными: `c.m.lib.graph_viewer.backend.api_server`.

**Решение**: 
- Использовать короткие идентификаторы: `c.m.graph_viewer` вместо `c.m.lib.graph_viewer`
- Или использовать хеши для очень длинных путей

---

## Структура JSON конфигурации

**Файл**: `config/vertex_styles.json`

```json
{
  "a.c": {
    "dark": {
      "color": "#1976D2",
      "border": "#0D47A1",
      "shape": "box"
    },
    "light": {
      "color": "#E3F2FD",
      "border": "#90CAF9",
      "shape": "box"
    }
  },
  "a.t": {
    "dark": {
      "color": "#388E3C",
      "border": "#1B5E20",
      "shape": "circle"
    },
    "light": {
      "color": "#E8F5E9",
      "border": "#81C784",
      "shape": "circle"
    }
  },
  "a.v": {
    "dark": {
      "color": "#7B1FA2",
      "border": "#4A148C",
      "shape": "diamond"
    },
    "light": {
      "color": "#F3E5F5",
      "border": "#BA68C8",
      "shape": "diamond"
    }
  },
  "c.m": {
    "dark": {
      "color": "#F57C00",
      "border": "#E65100",
      "shape": "box"
    },
    "light": {
      "color": "#FFF3E0",
      "border": "#FFB74D",
      "shape": "box"
    }
  },
  "c.comp": {
    "dark": {
      "color": "#5C6BC0",
      "border": "#283593",
      "shape": "box"
    },
    "light": {
      "color": "#E8EAF6",
      "border": "#7986CB",
      "shape": "box"
    }
  },
  "c.class": {
    "dark": {
      "color": "#00897B",
      "border": "#004D40",
      "shape": "box"
    },
    "light": {
      "color": "#B2DFDB",
      "border": "#4DB6AC",
      "shape": "box"
    }
  },
  "c.nested": {
    "dark": {
      "color": "#00695C",
      "border": "#003D33",
      "shape": "box"
    },
    "light": {
      "color": "#80CBC4",
      "border": "#26A69A",
      "shape": "box"
    }
  },
  "f.d": {
    "dark": {
      "color": "#757575",
      "border": "#424242",
      "shape": "box"
    },
    "light": {
      "color": "#E0E0E0",
      "border": "#9E9E9E",
      "shape": "box"
    }
  },
  "f.file": {
    "dark": {
      "color": "#616161",
      "border": "#212121",
      "shape": "box"
    },
    "light": {
      "color": "#F5F5F5",
      "border": "#BDBDBD",
      "shape": "box"
    }
  },
  "o.other": {
    "dark": {
      "color": "#2d3748",
      "border": "#4a5568",
      "shape": "box"
    },
    "light": {
      "color": "#ffffff",
      "border": "#e0e0e0",
      "shape": "box"
    }
  }
}
```

---

## Реализация

### Бакенд: Извлечение типа из ключа

**Важно**: Поле `arango_key` переименовывается в `key` (см. `migration-from-arango-key.md`)

```python
# utils/vertex_type.py
def extract_type_from_key(node_key: str) -> str:
    """
    Извлечь тип вершины из ключа
    
    Args:
        node_key: Ключ узла (например, "a.c.project", "c.m.graph_viewer")
    
    Returns:
        Ключ типа для визуализации (например, "a.c", "c.m")
    """
    # Новый формат: a.c.project
    if '.' in node_key:
        parts = node_key.split('.', 2)
        if len(parts) >= 2:
            segment, type_part = parts[0], parts[1]
            return f"{segment}.{type_part}"
    
    # Старый формат: c:project (для обратной совместимости)
    if ':' in node_key:
        prefix = node_key.split(':', 1)[0]
        prefix_mapping = {
            'c': 'a.c',
            't': 'a.t',
            'v': 'a.v',
            'm': 'c.m',
            'comp': 'c.comp',
            'd': 'f.d',
            'f': 'f.file'
        }
        return prefix_mapping.get(prefix, 'o.other')
    
    # Неизвестный формат
    return 'o.other'

def get_segment_from_key(node_key: str) -> str:
    """Извлечь сегмент из ключа"""
    type_key = extract_type_from_key(node_key)
    segment = type_key.split('.')[0]
    segment_mapping = {
        'a': 'architecture',
        'c': 'code_structure',
        'f': 'filesystem',
        'o': 'other'
    }
    return segment_mapping.get(segment, 'other')
```

### Фронтенд: Применение стилей

```javascript
// utils/visualization.js
import vertexStyles from '@/config/vertex_styles.json'

export function extractTypeFromKey(nodeKey) {
  // Новый формат: a.c.project
  if (nodeKey.includes('.') && !nodeKey.includes(':')) {
    const parts = nodeKey.split('.')
    if (parts.length >= 2) {
      return `${parts[0]}.${parts[1]}`
    }
  }
  
  // Старый формат: c:project (для обратной совместимости)
  if (nodeKey.includes(':')) {
    const prefix = nodeKey.split(':')[0]
    const prefixMapping = {
      'c': 'a.c',
      't': 'a.t',
      'v': 'a.v',
      'm': 'c.m',
      'comp': 'c.comp',
      'd': 'f.d',
      'f': 'f.file'
    }
    return prefixMapping[prefix] || 'o.other'
  }
  
  return 'o.other'
}

export function applyNodeVisualization(node, theme = 'light') {
  const nodeKey = node.key || node._key  // arango_key больше не используется
  const typeKey = extractTypeFromKey(nodeKey)
  const style = vertexStyles[typeKey]?.[theme] || vertexStyles['o.other'][theme]
  
  return {
    ...node,
    ...style,
    // Применить размеры
    ...(style.shape === 'box' && style.size ? {
      width: style.size.width,
      height: style.size.height,
      borderRadius: style.size.borderRadius
    } : {}),
    ...(style.shape === 'circle' && style.size ? {
      size: style.size.size
    } : {})
  }
}
```

### API: Создание узла

```python
# api_server_age.py
@app.route('/api/nodes', methods=['POST'])
def create_node():
    """Создать новый узел в графе"""
    data = request.json
    node_key = data.get('node_key')
    node_name = data.get('node_name')
    properties = data.get('properties', {})
    
    # Валидация: ключ должен быть в новом формате
    if not validate_new_key_format(node_key):
        return jsonify({'error': 'Ключ должен быть в формате {segment}.{type}.{identifier}'}), 400
    
    # Извлечь тип из ключа (не нужно передавать отдельно)
    type_key = extract_type_from_key(node_key)
    segment = get_segment_from_key(node_key)
    
    # Создать узел (node_type больше не нужен!)
    node_id = create_node_in_db(
        node_key=node_key,
        node_name=node_name,
        properties=properties
    )
    
    return jsonify({
        'node_id': node_id,
        'node_key': node_key,
        'type': type_key,
        'segment': segment
    })

def validate_new_key_format(node_key: str) -> bool:
    """Валидация формата ключа"""
    if not node_key or '.' not in node_key:
        return False
    
    parts = node_key.split('.')
    if len(parts) < 3:  # segment.type.identifier
        return False
    
    segment = parts[0]
    type_part = parts[1]
    
    # Проверить валидность сегмента
    valid_segments = ['a', 'c', 'f', 'o']
    if segment not in valid_segments:
        return False
    
    # Проверить валидность типа для сегмента
    valid_types = {
        'a': ['c', 't', 'v'],
        'c': ['m', 'comp', 'class', 'nested'],
        'f': ['d', 'file'],
        'o': ['other', 'custom']  # можно расширять
    }
    
    if type_part not in valid_types.get(segment, []):
        return False
    
    return True
```

---

## Сравнение подходов

| Аспект | Отдельное поле `node_type` | Тип в ключе |
|--------|---------------------------|-------------|
| Хранение | Два поля: `key` + `type` | Одно поле: `key` |
| Валидация | Нужно проверять соответствие | Автоматически валидно |
| Миграция | Не нужна | Нужна (один раз) |
| Читаемость | `c:project` + `type=concept` | `a.c.project` (самодокументируемо) |
| Длина ключа | Короткая | Длиннее на 2-3 символа |
| Обратная совместимость | ✅ | ⚠️ Нужна поддержка старого формата |
| Простота кода | ⚠️ Нужно синхронизировать | ✅ Проще |

---

## План миграции

### Этап 1: Поддержка обоих форматов
- Добавить функции нормализации ключей
- Обновить API для работы с обоими форматами
- Обновить фронтенд для поддержки обоих форматов

### Этап 2: Миграция данных
- Создать скрипт миграции ключей
- Выполнить миграцию в БД
- Проверить целостность данных

### Этап 3: Упрощение кода
- Удалить поле `node_type` из API
- Упростить валидацию
- Обновить документацию

---

## Рекомендация

✅ **Использовать подход с типом в ключе**, если:
- Готовы выполнить миграцию данных
- Нужна максимальная простота
- Тип узла всегда можно определить по ключу

⚠️ **Оставить отдельное поле**, если:
- Миграция данных сложна
- Нужна обратная совместимость без изменений
- Ключи могут быть в произвольном формате

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

