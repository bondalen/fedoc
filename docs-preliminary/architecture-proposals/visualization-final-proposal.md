# Финальное предложение: Улучшение системы визуализации

**Дата**: 2025-11-05  
**Статус**: Финальное предложение  
**Приоритет**: Высокий

---

## Уточнения от пользователя

1. **Префиксы новых типов**:
   - `file` → `f:`
   - `class` → `cl:`
   - `nested-class` → `cln:`

2. **Стили**: На усмотрение разработчика (потом можно исправить)

3. **Структура JSON**: Группировка по сегментам с общим цветом заливки

4. **Код**: На усмотрение разработчика

5. **Стили только на фронтенде**: Бакенд передаёт только `node_type`

6. **Хранилище истории**: В хранилище (10 состояний для undo/redo) тип узла не хранится — нужно добавить

---

## Анализ текущей ситуации

### Хранилище истории

**Файл**: `src/lib/graph_viewer/frontend/src/stores/graph.js`

**Текущая структура состояния**:
```javascript
const currentState = {
  startNode: startNode.value,
  depth: depth.value,
  project: project.value,
  nodeCount: nodeCount.value,
  edgeCount: edgeCount.value,
  nodes: getCurrentNodesData(), // Полные данные узлов из nodesDataSet
  edges: getCurrentEdgesData(),  // Полные данные рёбер из edgesDataSet
  timestamp: now
}
```

**Проблема**: В `nodes` из `nodesDataSet` может не быть поля `node_type`.

### Данные с бакенда

Бакенд передаёт узлы через API, но нужно проверить, передаётся ли `node_type`.

---

## Предложения

### 1. Добавить `node_type` в данные узлов

#### На бакенде

**Файл**: `src/lib/graph_viewer/backend/api_server_age.py`

Добавить `node_type` в данные узлов, передаваемые на фронтенд:

```python
def process_edge(edge_id, from_id, to_id, from_name, to_name, from_key, to_key, 
                 from_kind, to_kind, projects, rel_type, theme, project, 
                 nodes_map, edges_map):
    """Обработать ребро и добавить связанные узлы"""
    
    def get_node_type(node_key: str) -> str:
        """Определить тип узла по ключу"""
        if not node_key:
            return 'other'
        
        if node_key.startswith('c:'):
            return 'concept'
        elif node_key.startswith('t:'):
            return 'technology'
        elif node_key.startswith('v:'):
            return 'version'
        elif node_key.startswith('d:'):
            return 'directory'
        elif node_key.startswith('m:'):
            return 'module'
        elif node_key.startswith('comp:'):
            return 'component'
        elif node_key.startswith('f:'):
            return 'file'
        elif node_key.startswith('cl:'):
            return 'class'
        elif node_key.startswith('cln:'):
            return 'nested-class'
        else:
            return 'other'
    
    # Добавить узлы с node_type
    if from_id not in nodes_map:
        from_node_type = get_node_type(from_key)
        nodes_map[from_id] = {
            'id': from_id,
            'label': from_name,
            '_key': from_key,
            'node_type': from_node_type,  # ← добавить
            # ... остальные поля
        }
    
    if to_id not in nodes_map:
        to_node_type = get_node_type(to_key)
        nodes_map[to_id] = {
            'id': to_id,
            'label': to_name,
            '_key': to_key,
            'node_type': to_node_type,  # ← добавить
            # ... остальные поля
        }
```

#### На фронтенде

**Файл**: `src/lib/graph_viewer/frontend/src/stores/graph.js`

При загрузке данных с бакенда сохранять `node_type`:

```javascript
const loadGraph = async () => {
  // ... загрузка данных
  
  // При добавлении узлов в nodesDataSet сохранять node_type
  nodes.forEach(node => {
    if (!node.node_type && node._key) {
      node.node_type = getNodeType(node._key)  // Определить если нет
    }
    nodesDataSet.value.add(node)
  })
}
```

### 2. Доработать JSON конфигурацию

**Файл**: `src/lib/graph_viewer/frontend/src/config/visualization.json`

**Структура с группировкой по сегментам**:

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
  "segments": {
    "architecture": {
      "dark": {
        "color": "#1976D2",
        "border": "#0D47A1",
        "font": {
          "color": "#ffffff",
          "size": 12,
          "strokeWidth": 2,
          "strokeColor": "#1976D2"
        }
      },
      "light": {
        "color": "#E3F2FD",
        "border": "#90CAF9",
        "font": {
          "color": "#000000",
          "size": 12,
          "strokeWidth": 2,
          "strokeColor": "#E3F2FD"
        }
      },
      "types": {
        "concept": {
          "type": "concept",
          "shape": "box",
          "size": { "width": 120, "height": 36, "borderRadius": 6, "borderWidth": 1, "margin": 10 }
        },
        "technology": {
          "type": "technology",
          "shape": "circle",
          "size": { "size": 36, "borderWidth": 1, "margin": 10 }
        },
        "version": {
          "type": "version",
          "shape": "diamond",
          "size": { "size": 24, "borderWidth": 1, "margin": 10 }
        }
      }
    },
    "code_structure": {
      "dark": {
        "color": "#F57C00",
        "border": "#E65100",
        "font": {
          "color": "#ffffff",
          "size": 11,
          "strokeWidth": 1,
          "strokeColor": "#F57C00"
        }
      },
      "light": {
        "color": "#FFF3E0",
        "border": "#FFB74D",
        "font": {
          "color": "#000000",
          "size": 11,
          "strokeWidth": 1,
          "strokeColor": "#FFF3E0"
        }
      },
      "types": {
        "module": {
          "type": "module",
          "shape": "box",
          "size": { "width": 140, "height": 40, "borderRadius": 4, "borderWidth": 1, "margin": 10 }
        },
        "component": {
          "type": "component",
          "shape": "box",
          "size": { "width": 130, "height": 38, "borderRadius": 5, "borderWidth": 1, "margin": 10 }
        },
        "class": {
          "type": "class",
          "shape": "box",
          "size": { "width": 120, "height": 35, "borderRadius": 3, "borderWidth": 1, "margin": 10 }
        },
        "nested-class": {
          "type": "nested-class",
          "shape": "box",
          "size": { "width": 110, "height": 32, "borderRadius": 2, "borderWidth": 1, "margin": 10 }
        }
      }
    },
    "filesystem": {
      "dark": {
        "color": "#757575",
        "border": "#424242",
        "font": {
          "color": "#ffffff",
          "size": 10,
          "strokeWidth": 0,
          "strokeColor": "transparent"
        }
      },
      "light": {
        "color": "#E0E0E0",
        "border": "#9E9E9E",
        "font": {
          "color": "#000000",
          "size": 10,
          "strokeWidth": 0,
          "strokeColor": "transparent"
        }
      },
      "types": {
        "directory": {
          "type": "directory",
          "shape": "box",
          "size": { "width": 150, "height": 30, "borderRadius": 0, "borderWidth": 1, "margin": 10 }
        },
        "file": {
          "type": "file",
          "shape": "box",
          "size": { "width": 140, "height": 28, "borderRadius": 0, "borderWidth": 1, "margin": 10 }
        }
      }
    },
    "other": {
      "dark": {
        "color": "#2d3748",
        "border": "#4a5568",
        "font": {
          "color": "#ffffff",
          "size": 12,
          "strokeWidth": 2,
          "strokeColor": "#2d3748"
        }
      },
      "light": {
        "color": "#ffffff",
        "border": "#e0e0e0",
        "font": {
          "color": "#000000",
          "size": 12,
          "strokeWidth": 2,
          "strokeColor": "#ffffff"
        }
      },
      "types": {
        "other": {
          "type": "other",
          "shape": "box",
          "size": { "width": 120, "height": 36, "borderRadius": 6, "borderWidth": 1, "margin": 10 }
        }
      }
    }
  },
  "edges": { ... },
  "states": { ... }
}
```

### 3. Создать утилиту определения типа

**Файл**: `src/lib/graph_viewer/frontend/src/utils/nodeType.js`

```javascript
/**
 * Маппинг префиксов ключей на типы узлов
 */
const NODE_TYPE_MAPPING = {
  'c:': 'concept',
  't:': 'technology',
  'v:': 'version',
  'd:': 'directory',
  'm:': 'module',
  'comp:': 'component',
  'f:': 'file',
  'cl:': 'class',
  'cln:': 'nested-class'
}

/**
 * Определить тип узла по ключу
 * @param {string} nodeKey - ключ узла
 * @returns {string} тип узла
 */
export function getNodeType(nodeKey) {
  if (!nodeKey) return 'other'
  
  for (const [prefix, nodeType] of Object.entries(NODE_TYPE_MAPPING)) {
    if (nodeKey.startsWith(prefix)) {
      return nodeType
    }
  }
  
  return 'other'
}

/**
 * Определить сегмент по типу узла
 * @param {string} nodeType - тип узла
 * @returns {string} сегмент
 */
export function getSegmentByType(nodeType) {
  const segmentMapping = {
    'concept': 'architecture',
    'technology': 'architecture',
    'version': 'architecture',
    'module': 'code_structure',
    'component': 'code_structure',
    'class': 'code_structure',
    'nested-class': 'code_structure',
    'directory': 'filesystem',
    'file': 'filesystem',
    'other': 'other'
  }
  
  return segmentMapping[nodeType] || 'other'
}
```

### 4. Обновить функцию визуализации

**Файл**: `src/lib/graph_viewer/frontend/src/utils/visualization.js`

```javascript
import visualizationConfig from '@/config/visualization.json'
import { getNodeType, getSegmentByType } from '@/utils/nodeType'

/**
 * Применить оформление к узлу
 * @param {Object} node - узел с полями {id, key, label, node_type}
 * @param {string} theme - 'dark' или 'light'
 * @param {boolean} isSelected - выделен ли узел
 * @param {boolean} isHovered - наведён ли курсор
 * @returns {Object} узел с применённым оформлением
 */
export const applyNodeVisualization = (node, theme, isSelected = false, isHovered = false) => {
  // Определить тип узла (из node.node_type или по ключу)
  const nodeType = node.node_type || getNodeType(node.key || node._key)
  
  // Определить сегмент
  const segment = getSegmentByType(nodeType)
  
  // Получить конфигурацию стиля
  const segmentConfig = visualizationConfig.segments[segment]
  if (!segmentConfig) {
    // Fallback на default
    const defaultConfig = visualizationConfig.default.nodes[theme]
    return applyDefaultStyle(node, defaultConfig, theme, isSelected, isHovered)
  }
  
  // Получить оформление сегмента для темы (цвета, границы, шрифт)
  const segmentThemeConfig = segmentConfig[theme]
  if (!segmentThemeConfig) {
    // Fallback на default
    const defaultConfig = visualizationConfig.default.nodes[theme]
    return applyDefaultStyle(node, defaultConfig, theme, isSelected, isHovered)
  }
  
  // Получить конфигурацию типа узла (форма, размеры)
  const typeConfig = segmentConfig.types[nodeType]
  if (!typeConfig) {
    // Fallback на default
    const defaultConfig = visualizationConfig.default.nodes[theme]
    return applyDefaultStyle(node, defaultConfig, theme, isSelected, isHovered)
  }
  
  // Получить форму и размеры из типа узла
  const shape = typeConfig.shape
  const size = typeConfig.size
  
  // Получить дефолтную конфигурацию для fallback
  const defaultConfig = visualizationConfig.default.nodes[theme]
  
  // Применить стиль: оформление из сегмента + форма/размеры из типа
  return applyStyle(node, shape, size, segmentThemeConfig, defaultConfig, theme, isSelected, isHovered)
}

function applyStyle(node, shape, size, segmentThemeConfig, defaultConfig, theme, isSelected, isHovered) {
  // Размеры и форма не зависят от темы - берём из typeConfig
  const sizeConfig = size || defaultConfig.size || {}
  const borderWidth = sizeConfig.borderWidth || 1
  const actualBorderWidth = isSelected 
    ? visualizationConfig.states.selected.width 
    : borderWidth
  
  // Оформление берём из сегмента (цвета, границы, шрифт)
  let visualNode = {
    ...node,
    node_type: node.node_type || getNodeType(node.key || node._key),  // Сохранить тип
    color: {
      background: node.color?.background || segmentThemeConfig.color,
      border: node.color?.border || segmentThemeConfig.border,
      highlight: {
        background: node.color?.background || segmentThemeConfig.color,
        border: isSelected 
          ? visualizationConfig.states.selected.border 
          : isHovered 
            ? visualizationConfig.states.hover.border 
            : (node.color?.border || segmentThemeConfig.border)
      },
      hover: {
        background: node.color?.background || segmentThemeConfig.color,
        border: visualizationConfig.states.hover.border
      }
    },
    shape: node.shape || shape,  // Из typeConfig (не зависит от темы)
    font: {
      color: node.font?.color || segmentThemeConfig.font.color,
      size: node.font?.size || segmentThemeConfig.font.size,
      strokeWidth: segmentThemeConfig.font?.strokeWidth || defaultConfig.font?.strokeWidth || 0,
      strokeColor: segmentThemeConfig.font?.strokeColor || defaultConfig.font?.strokeColor || 'transparent'
    },
    borderWidth: node.borderWidth || actualBorderWidth,
    borderWidthSelected: visualizationConfig.states.selected.width
  }
  
  // Применить размеры в зависимости от формы (не зависят от темы)
  if (sizeConfig) {
    if (shape === 'box' && sizeConfig.width && sizeConfig.height) {
      visualNode.width = node.width || sizeConfig.width
      visualNode.height = node.height || sizeConfig.height
      if (sizeConfig.borderRadius !== undefined) {
        visualNode.borderRadius = sizeConfig.borderRadius
      }
    } else if ((shape === 'circle' || shape === 'dot') && sizeConfig.size) {
      visualNode.size = node.size || sizeConfig.size
    } else if (shape === 'diamond' && sizeConfig.size) {
      visualNode.size = node.size || sizeConfig.size
    }
    
    if (sizeConfig.margin !== undefined) {
      visualNode.margin = sizeConfig.margin
    }
  }
  
  return visualNode
}

function applyDefaultStyle(node, defaultConfig, theme, isSelected, isHovered) {
  // Применить дефолтный стиль
  // ... аналогично applyStyle
}
```

### 5. Обновить хранилище

**Файл**: `src/lib/graph_viewer/frontend/src/stores/graph.js`

При сохранении состояния убедиться, что `node_type` есть в узлах:

```javascript
const getCurrentNodesData = () => {
  if (!nodesDataSet.value) return []
  
  const nodes = nodesDataSet.value.get()
  
  // Убедиться, что у всех узлов есть node_type
  return nodes.map(node => {
    if (!node.node_type && (node.key || node._key)) {
      node.node_type = getNodeType(node.key || node._key)
    }
    return node
  })
}
```

---

## План реализации

1. ✅ Добавить `node_type` в данные узлов на бакенде
2. ✅ Создать утилиту `getNodeType()` на фронтенде
3. ✅ Доработать JSON конфигурацию с группировкой по сегментам
4. ✅ Обновить функцию `applyNodeVisualization()` для работы с сегментами
5. ✅ Обновить хранилище для сохранения `node_type` в истории
6. ✅ Обновить валидацию на бакенде для новых типов (`f:`, `cl:`, `cln:`)

---

## Преимущества

✅ **Разделение процессов**: Наполнение хранилища и отрисовка разделены  
✅ **Тип в хранилище**: `node_type` сохраняется в истории  
✅ **Единообразность**: Один способ определения типа  
✅ **Группировка по сегментам**: Общий цвет заливки для сегмента  
✅ **Расширяемость**: Легко добавить новые типы  

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

