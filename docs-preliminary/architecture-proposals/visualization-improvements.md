# Улучшение системы визуализации узлов

**Дата**: 2025-11-05  
**Статус**: Предложение  
**Приоритет**: Высокий

---

## Текущая ситуация

### Типы узлов в системе
- `concept` (префикс `c:`) — концепты проекта
- `technology` (префикс `t:`) — технологии
- `version` (префикс `v:`) — версии технологий
- `directory` (префикс `d:`) — директории
- `module` (префикс `m:`) — модули
- `component` (префикс `comp:`) — компоненты
- `other` — прочие

### Новые типы (нужно добавить)
- `file` (префикс `f:`) — файлы
- `class` (префикс `class:`) — классы
- `nested-class` (префикс `nested:`) — вложенные классы

### Проблемы
1. В JSON только 3 типа: `category`, `technology`, `version`
2. Код определения типа разбросан (фронтенд и бакенд)
3. Нет единообразного применения стилей
4. Новые типы не имеют стилей

---

## Предложения

### 1. Доработать JSON конфигурацию

**Файл**: `src/lib/graph_viewer/frontend/src/config/visualization.json`

**Структура**:
```json
{
  "default": {
    "nodes": { ... },
    "edges": { ... }
  },
  "nodes": {
    "concept": { ... },      // было "category"
    "technology": { ... },
    "version": { ... },
    "directory": { ... },     // новый
    "module": { ... },        // новый
    "component": { ... },     // новый
    "file": { ... },          // новый
    "class": { ... },         // новый
    "nested-class": { ... }   // новый
  },
  "edges": { ... },
  "states": { ... }
}
```

### 2. Единообразное определение типа

**Создать утилиту**: `src/lib/graph_viewer/shared/node_type_utils.py` (Python) и `src/lib/graph_viewer/frontend/src/utils/nodeType.js` (JavaScript)

**Маппинг префиксов на типы**:
```python
# Python
NODE_TYPE_MAPPING = {
    'c:': 'concept',
    't:': 'technology',
    'v:': 'version',
    'd:': 'directory',
    'm:': 'module',
    'comp:': 'component',
    'f:': 'file',
    'class:': 'class',
    'nested:': 'nested-class'
}

def get_node_type(node_key: str) -> str:
    """Определить тип узла по ключу"""
    if not node_key:
        return 'other'
    
    for prefix, node_type in NODE_TYPE_MAPPING.items():
        if node_key.startswith(prefix):
            return node_type
    
    return 'other'
```

```javascript
// JavaScript
const NODE_TYPE_MAPPING = {
  'c:': 'concept',
  't:': 'technology',
  'v:': 'version',
  'd:': 'directory',
  'm:': 'module',
  'comp:': 'component',
  'f:': 'file',
  'class:': 'class',
  'nested:': 'nested-class'
}

export function getNodeType(nodeKey) {
  if (!nodeKey) return 'other'
  
  for (const [prefix, nodeType] of Object.entries(NODE_TYPE_MAPPING)) {
    if (nodeKey.startsWith(prefix)) {
      return nodeType
    }
  }
  
  return 'other'
}
```

### 3. Единообразное применение стилей

**Фронтенд**: Использовать `getNodeType()` и применять стили из JSON

**Бакенд**: Использовать `get_node_type()` и применять стили из JSON (или передавать тип на фронтенд)

---

## Вопросы для уточнения

1. **Префиксы для новых типов**:
   - `file` → `f:` (подтвердить?)
   - `class` → `class:` (подтвердить?)
   - `nested-class` → `nested:` (подтвердить?)

2. **Стили для новых типов**:
   - Какие цвета/формы для `directory`, `module`, `component`, `file`, `class`, `nested-class`?
   - Использовать существующие цвета или новые?

3. **Сегменты в JSON**:
   - Нужно ли группировать типы по сегментам в JSON?
   - Или оставить плоскую структуру `nodes.{type}`?

4. **Бакенд стилизация**:
   - Нужно ли применять стили на бакенде?
   - Или только передавать `node_type` на фронтенд?

---

## Предлагаемая структура JSON

```json
{
  "default": {
    "nodes": {
      "dark": { ... },
      "light": { ... }
    },
    "edges": {
      "dark": { ... },
      "light": { ... }
    }
  },
  "nodes": {
    "concept": {
      "dark": {
        "color": "#1976D2",
        "border": "#0D47A1",
        "shape": "box",
        "size": { "width": 120, "height": 36, "borderRadius": 6 }
      },
      "light": { ... }
    },
    "technology": { ... },
    "version": { ... },
    "directory": {
      "dark": {
        "color": "#757575",
        "border": "#424242",
        "shape": "box",
        "size": { "width": 150, "height": 30, "borderRadius": 0 }
      },
      "light": { ... }
    },
    "module": {
      "dark": {
        "color": "#F57C00",
        "border": "#E65100",
        "shape": "box",
        "size": { "width": 140, "height": 40, "borderRadius": 4 }
      },
      "light": { ... }
    },
    "component": {
      "dark": {
        "color": "#5C6BC0",
        "border": "#283593",
        "shape": "box",
        "size": { "width": 130, "height": 38, "borderRadius": 5 }
      },
      "light": { ... }
    },
    "file": {
      "dark": {
        "color": "#616161",
        "border": "#212121",
        "shape": "box",
        "size": { "width": 140, "height": 28, "borderRadius": 0 }
      },
      "light": { ... }
    },
    "class": {
      "dark": {
        "color": "#00897B",
        "border": "#004D40",
        "shape": "box",
        "size": { "width": 120, "height": 35, "borderRadius": 3 }
      },
      "light": { ... }
    },
    "nested-class": {
      "dark": {
        "color": "#00695C",
        "border": "#003D33",
        "shape": "box",
        "size": { "width": 110, "height": 32, "borderRadius": 2 }
      },
      "light": { ... }
    },
    "other": {
      "dark": { ... },
      "light": { ... }
    }
  },
  "edges": { ... },
  "states": { ... }
}
```

---

## План реализации

1. ✅ Доработать JSON с новыми типами
2. ✅ Создать утилиту `getNodeType()` (Python и JavaScript)
3. ✅ Обновить код на фронтенде для использования `getNodeType()`
4. ✅ Обновить код на бакенде для использования `get_node_type()`
5. ✅ Убрать дублирование кода определения типа

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

