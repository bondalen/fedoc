# Структура данных в хранилище истории

**Дата**: 2025-11-05  
**Вопрос**: В каком виде хранятся данные узлов и рёбер в хранилище?

---

## Текущая реализация

### Хранение в памяти

Данные хранятся как **объекты JavaScript** в памяти, не в строчном виде.

**Код**:
```javascript
const getCurrentNodesData = () => {
  if (!nodesDataSet.value) return []
  return nodesDataSet.value.get()  // Возвращает массив объектов
}

const getCurrentEdgesData = () => {
  if (!edgesDataSet.value) return []
  return edgesDataSet.value.get()  // Возвращает массив объектов
}

const currentState = {
  startNode: startNode.value,
  depth: depth.value,
  project: project.value,
  nodeCount: nodeCount.value,
  edgeCount: edgeCount.value,
  nodes: getCurrentNodesData(),  // Массив объектов узлов
  edges: getCurrentEdgesData(),  // Массив объектов рёбер
  timestamp: now
}

viewHistory.value.push(currentState)  // Сохраняется как объект
```

---

## Пример структуры данных

### Состояние в хранилище

```javascript
{
  startNode: "c:project",
  depth: 5,
  project: "fedoc",
  nodeCount: 15,
  edgeCount: 23,
  timestamp: 1699123456789,
  nodes: [
    {
      id: 844424930131969,
      label: "Проект",
      _key: "c:project",
      node_type: "concept",  // ← нужно добавить
      color: {
        background: "#1976D2",
        border: "#0D47A1",
        highlight: {
          background: "#1976D2",
          border: "#D2691E"
        },
        hover: {
          background: "#1976D2",
          border: "#9c27b0"
        }
      },
      shape: "box",
      width: 120,
      height: 36,
      borderRadius: 6,
      font: {
        color: "#ffffff",
        size: 12,
        strokeWidth: 2,
        strokeColor: "#1976D2"
      },
      borderWidth: 1
    },
    {
      id: 844424930131972,
      label: "Python",
      _key: "t:python",
      node_type: "technology",  // ← нужно добавить
      color: {
        background: "#388E3C",
        border: "#1B5E20"
      },
      shape: "circle",
      size: 36,
      font: {
        color: "#ffffff",
        size: 12,
        strokeWidth: 2,
        strokeColor: "#388E3C"
      },
      borderWidth: 1
    },
    {
      id: 844424930131975,
      label: "graph_viewer",
      _key: "m:graph_viewer",
      node_type: "module",  // ← нужно добавить
      color: {
        background: "#F57C00",
        border: "#E65100"
      },
      shape: "box",
      width: 140,
      height: 40,
      borderRadius: 4,
      font: {
        color: "#ffffff",
        size: 11,
        strokeWidth: 1,
        strokeColor: "#F57C00"
      },
      borderWidth: 1
    }
  ],
  edges: [
    {
      id: 12345,
      from: 844424930131969,
      to: 844424930131972,
      label: "fedoc",
      color: {
        color: "#64B5F6",
        highlight: "#D2691E",
        hover: "#9c27b0"
      },
      width: 2,
      font: {
        color: "#e0e0e0",
        size: 12,
        strokeWidth: 2
      }
    },
    {
      id: 12346,
      from: 844424930131969,
      to: 844424930131975,
      label: "fedoc",
      color: {
        color: "#64B5F6",
        highlight: "#D2691E",
        hover: "#9c27b0"
      },
      width: 2
    }
  ]
}
```

---

## Проблема: отсутствие `node_type`

**Текущая ситуация**: В узлах может отсутствовать поле `node_type`.

**Решение**: Добавить `node_type` при сохранении:

```javascript
const getCurrentNodesData = () => {
  if (!nodesDataSet.value) return []
  
  const nodes = nodesDataSet.value.get()
  
  // Убедиться, что у всех узлов есть node_type
  return nodes.map(node => {
    if (!node.node_type && (node._key || node.key)) {
      node.node_type = getNodeType(node._key || node.key)
    }
    return node
  })
}
```

---

## Сериализация (если нужна)

Если нужно сохранить в localStorage или отправить на сервер, данные сериализуются в JSON:

```javascript
// Сериализация в строку
const stateString = JSON.stringify(currentState)
localStorage.setItem('graphState', stateString)

// Десериализация из строки
const stateString = localStorage.getItem('graphState')
const currentState = JSON.parse(stateString)
```

**Пример JSON строки**:
```json
{
  "startNode": "c:project",
  "depth": 5,
  "project": "fedoc",
  "nodeCount": 15,
  "edgeCount": 23,
  "timestamp": 1699123456789,
  "nodes": [
    {
      "id": 844424930131969,
      "label": "Проект",
      "_key": "c:project",
      "node_type": "concept",
      "color": {
        "background": "#1976D2",
        "border": "#0D47A1"
      },
      "shape": "box",
      "width": 120,
      "height": 36
    }
  ],
  "edges": [
    {
      "id": 12345,
      "from": 844424930131969,
      "to": 844424930131972,
      "label": "fedoc",
      "color": {
        "color": "#64B5F6"
      }
    }
  ]
}
```

---

## Рекомендация

### Хранение в памяти (текущее)

✅ **Оставить как есть**: Данные хранятся как объекты JavaScript в памяти  
✅ **Добавить `node_type`**: При сохранении убедиться, что у всех узлов есть `node_type`  

### Если нужна персистентность

Если нужно сохранить историю между сессиями:

```javascript
// При сохранении состояния
const stateString = JSON.stringify(currentState)
localStorage.setItem(`graphHistory_${currentHistoryIndex.value}`, stateString)

// При загрузке
const stateString = localStorage.getItem(`graphHistory_${index}`)
const state = JSON.parse(stateString)
```

---

## Итоговая структура узла в хранилище

```javascript
{
  id: 844424930131969,              // Числовой ID (AGE ID)
  label: "Проект",                   // Отображаемое имя
  _key: "c:project",                 // Ключ узла
  node_type: "concept",             // Тип узла (нужно добавить)
  color: { ... },                   // Цвета (из визуализации)
  shape: "box",                     // Форма
  width: 120,                       // Размеры
  height: 36,
  font: { ... },                    // Параметры шрифта
  borderWidth: 1                    // Ширина границы
}
```

**Важно**: 
- Данные хранятся как **объекты** в памяти
- При необходимости могут быть сериализованы в JSON строку
- Нужно добавить `node_type` при сохранении

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

