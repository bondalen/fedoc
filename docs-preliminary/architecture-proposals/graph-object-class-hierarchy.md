# Иерархия классов GraphObject

**Дата**: 2025-11-04  
**Статус**: Предложение  
**Цель**: Централизация визуализации через классы

---

## Проблема

Стили для визуализации берутся из разных источников:
1. `visualization.json` — частично используется
2. `GraphCanvas.vue` — хардкод опций vis-network
3. `stores/graph.js` — функция `applyTheme()` перезаписывает стили

**Результат**: Canvas и SVG выглядят по-разному.

---

## Решение: Иерархия классов

### Базовая структура

```
GraphObject (абстрактный базовый класс)
├── GraphVertex (абстрактный класс для вершин)
│   ├── ConceptVertex (концепт)
│   │   ├── ProjectConceptVertex (c:project)
│   │   ├── BackendConceptVertex (c:backend)
│   │   ├── FrontendConceptVertex (c:frontend)
│   │   └── ...
│   ├── TechnologyVertex (технология)
│   │   ├── JavaTechnologyVertex (t:java)
│   │   ├── PostgresTechnologyVertex (t:postgres)
│   │   ├── VueTechnologyVertex (t:vue)
│   │   └── ...
│   ├── VersionVertex (версия)
│   │   ├── JavaVersionVertex (v:java@21)
│   │   ├── PostgresVersionVertex (v:postgres@16)
│   │   └── ...
│   └── DefaultVertex (прочие узлы)
│
└── GraphEdge (рёбра)
    ├── UsesEdge (uses)
    ├── DependsEdge (depends)
    ├── RelatedEdge (related)
    ├── ContainsEdge (contains)
    └── ...
```

---

## Детальное описание классов

### GraphObject (базовый)

**Файл**: `src/lib/graph_viewer/frontend/src/models/base.js`

```javascript
export class GraphObject {
  constructor(id, createdAt = null, updatedAt = null) {
    this.id = id
    this.createdAt = createdAt || new Date()
    this.updatedAt = updatedAt || new Date()
  }
  
  // === Методы рендеринга ===
  
  /**
   * Формат для vis-network
   * @abstract
   */
  toVisNetworkFormat(theme, state = 'default') {
    throw new Error('toVisNetworkFormat must be implemented')
  }
  
  /**
   * Формат для SVG
   * @abstract
   */
  toSVGFormat(theme, position) {
    throw new Error('toSVGFormat must be implemented')
  }
  
  // === Методы стилизации ===
  
  /**
   * Получить базовый стиль из конфига
   * @abstract
   */
  getVisualStyle(theme) {
    throw new Error('getVisualStyle must be implemented')
  }
  
  /**
   * Получить стиль для интерактивного состояния
   */
  getInteractionStyle(state) {
    const config = visualizationConfig.states
    switch (state) {
      case 'selected':
        return { border: config.selected.border, borderWidth: config.selected.width }
      case 'hover':
        return { border: config.hover.border }
      default:
        return {}
    }
  }
  
  // === Сериализация ===
  
  toDict() {
    return {
      id: this.id,
      created_at: this.createdAt.toISOString(),
      updated_at: this.updatedAt.toISOString()
    }
  }
  
  static fromDict(data) {
    throw new Error('fromDict must be implemented')
  }
  
  toJSON() {
    return JSON.stringify(this.toDict())
  }
  
  static fromJSON(jsonStr) {
    return this.fromDict(JSON.parse(jsonStr))
  }
  
  // === Валидация ===
  
  validate() {
    return !!this.id
  }
}
```

---

### GraphVertex (базовый для вершин)

**Файл**: `src/lib/graph_viewer/frontend/src/models/vertices/GraphVertex.js`

```javascript
import { GraphObject } from '../base.js'
import visualizationConfig from '@/config/visualization.json'

export class GraphVertex extends GraphObject {
  constructor(id, key, label, properties = {}) {
    super(id)
    this.key = key
    this.label = label
    this.properties = properties
    this.nodeType = this.inferType()
  }
  
  // === Определение типа ===
  
  inferType() {
    if (this.key.startsWith('c:')) return 'concept'
    if (this.key.startsWith('t:')) return 'technology'
    if (this.key.startsWith('v:')) return 'version'
    return 'default'
  }
  
  // === Стилизация ===
  
  getVisualStyle(theme) {
    const typeConfig = visualizationConfig.nodes[this.nodeType] || visualizationConfig.default.nodes
    const themeConfig = typeConfig[theme]
    
    return {
      color: themeConfig.color,
      border: themeConfig.border,
      shape: themeConfig.shape,
      size: themeConfig.size,
      font: themeConfig.font
    }
  }
  
  // === Рендеринг для vis-network ===
  
  toVisNetworkFormat(theme, state = 'default') {
    const baseStyle = this.getVisualStyle(theme)
    const interactionStyle = this.getInteractionStyle(state)
    
    const visNode = {
      id: this.id,
      label: this.label,
      title: this.getTooltip(),
      shape: baseStyle.shape,
      color: {
        background: baseStyle.color,
        border: interactionStyle.border || baseStyle.border,
        highlight: {
          background: baseStyle.color,
          border: visualizationConfig.states.selected.border
        },
        hover: {
          background: baseStyle.color,
          border: visualizationConfig.states.hover.border
        }
      },
      font: {
        color: baseStyle.font.color,
        size: baseStyle.font.size,
        strokeWidth: baseStyle.font.strokeWidth,
        strokeColor: baseStyle.font.strokeColor
      },
      borderWidth: interactionStyle.borderWidth || baseStyle.size.borderWidth,
      borderWidthSelected: visualizationConfig.states.selected.width
    }
    
    // Применить размеры в зависимости от формы
    if (baseStyle.shape === 'box') {
      visNode.width = baseStyle.size.width
      visNode.height = baseStyle.size.height
      if (baseStyle.size.borderRadius !== undefined) {
        visNode.borderRadius = baseStyle.size.borderRadius
      }
    } else if (baseStyle.shape === 'circle' || baseStyle.shape === 'dot') {
      visNode.size = baseStyle.size.size
    } else if (baseStyle.shape === 'diamond') {
      visNode.size = baseStyle.size.size
    }
    
    if (baseStyle.size.margin !== undefined) {
      visNode.margin = baseStyle.size.margin
    }
    
    return visNode
  }
  
  // === Рендеринг для SVG ===
  
  toSVGFormat(theme, position) {
    const style = this.getVisualStyle(theme)
    return this._renderSVG(style, position)
  }
  
  _renderSVG(style, position) {
    const { x, y } = position
    const { shape, color, border, size, font } = style
    
    let nodeElement = ''
    let textX = x
    let textY = y
    
    // Рендер фигуры
    if (shape === 'box') {
      const width = size.width
      const height = size.height
      const borderRadius = size.borderRadius || 0
      
      nodeElement = `
        <rect
          x="${x - width/2}"
          y="${y - height/2}"
          width="${width}"
          height="${height}"
          rx="${borderRadius}"
          ry="${borderRadius}"
          fill="${color}"
          stroke="${border}"
          stroke-width="${size.borderWidth}"
        />
      `
    } else if (shape === 'circle') {
      const radius = size.size / 2
      
      nodeElement = `
        <circle
          cx="${x}"
          cy="${y}"
          r="${radius}"
          fill="${color}"
          stroke="${border}"
          stroke-width="${size.borderWidth}"
        />
      `
    } else if (shape === 'diamond') {
      const size_val = size.size
      const half = size_val / 2
      
      nodeElement = `
        <polygon
          points="${x},${y-half} ${x+half},${y} ${x},${y+half} ${x-half},${y}"
          fill="${color}"
          stroke="${border}"
          stroke-width="${size.borderWidth}"
        />
      `
    }
    
    // Рендер текста (двойной слой)    // Рендер текста (двойной слой)
    let textElement = ''
    
    if (font.strokeWidth > 0) {
      // Слой 1: обводка
      textElement += `
        <text
          x="${textX}" y="${textY}"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="none"
          stroke="${font.strokeColor}"
          stroke-width="${font.strokeWidth}"
          font-size="${font.size}"
          font-family="sans-serif"
        >${this.escapeXml(this.label)}</text>
      `
    }
    
    // Слой 2: основной текст
    textElement += `
      <text
        x="${textX}" y="${textY}"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="${font.color}"
        font-size="${font.size}"
        font-family="sans-serif"
      >${this.escapeXml(this.label)}</text>
    `
    
    return nodeElement + textElement
  }
  
  // === Сериализация ===
  
  toDict() {
    return {
      ...super.toDict(),
      key: this.key,
      label: this.label,
      node_type: this.nodeType,
      properties: this.properties
    }
  }
  
  static fromDict(data) {
    // Фабрика классов - выбор по ключу
    const key = data.key || ''
    
    if (key.startsWith('c:')) {
      return ConceptVertex.fromDict(data)
    } else if (key.startsWith('t:')) {
      return TechnologyVertex.fromDict(data)
    } else if (key.startsWith('v:')) {
      return VersionVertex.fromDict(data)
    } else {
      return new GraphVertex(
        data.id,
        data.key,
        data.label,
        data.properties || {}
      )
    }
  }
  
  validate() {
    if (!super.validate()) return false
    if (!this.key || !this.label) return false
    return true
  }
  
  getTooltip() {
    return `${this.label}\n${this.key}`
  }
  
  escapeXml(text) {
    if (!text) return ''
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }
}
```

---

### ConceptVertex

**Файл**: `src/lib/graph_viewer/frontend/src/models/vertices/ConceptVertex.js`

```javascript
import { GraphVertex } from './GraphVertex.js'

export class ConceptVertex extends GraphVertex {
  constructor(id, key, label, properties = {}) {
    super(id, key, label, properties)
  }
  
  // Переопределить тултип
  getTooltip() {
    return `Концепт: ${this.label}\n${this.key}`
  }
}
```

---

### GraphEdge

**Файл**: `src/lib/graph_viewer/frontend/src/models/edges/GraphEdge.js`

```javascript
import { GraphObject } from '../base.js'
import visualizationConfig from '@/config/visualization.json'

export class GraphEdge extends GraphObject {
  constructor(id, fromId, toId, type = 'uses', projects = []) {
    super(id)
    this.fromId = fromId
    this.toId = toId
    this.type = type
    this.projects = projects
  }
  
  // === Стилизация ===
  
  getVisualStyle(theme) {
    const edgeConfig = visualizationConfig.edges[this.type] || visualizationConfig.edges.uses
    const defaultConfig = visualizationConfig.default.edges[theme]
    const smoothConfig = visualizationConfig.edges.smooth || {}
    
    return {
      color: edgeConfig.color,
      width: defaultConfig.width,
      dashes: edgeConfig.dashes ? '6 4' : 'none',
      smooth: smoothConfig,
      font: defaultConfig.font
    }
  }
  
  // === Рендеринг для vis-network ===
  
  toVisNetworkFormat(theme, state = 'default') {
    const style = this.getVisualStyle(theme)
    const interactionStyle = this.getInteractionStyle(state)
    
    return {
      id: this.id,
      from: this.fromId,
      to: this.toId,
      label: this.projects.join(', '),
      arrows: {
        to: { enabled: true, scaleFactor: 0.5 }
      },
      color: {
        color: style.color,
        highlight: interactionStyle.border || visualizationConfig.states.selected.border,
        hover: visualizationConfig.states.hover.border
      },
      width: style.width,
      font: style.font,
      dashes: style.dashes !== 'none' ? [6, 4] : false,
      smooth: {
        enabled: style.smooth.type === 'cubicBezier',
        type: style.smooth.type,
        forceDirection: style.smooth.forceDirection,
        roundness: style.smooth.roundness
      }
    }
  }
  
  // === Рендеринг для SVG ===
  
  toSVGFormat(theme, fromPos, toPos) {
    const style = this.getVisualStyle(theme)
    return this._renderSVG(style, fromPos, toPos)
  }
  
  _renderSVG(style, fromPos, toPos) {
    const { color, width, dashes, smooth } = style
    
    // Вычислить направление для смещения от границы узла
    const dx = toPos.x - fromPos.x
    const dy = toPos.y - fromPos.y
    const length = Math.sqrt(dx * dx + dy * dy)
    
    if (length === 0) return ''
    
    const nx = dx / length
    const ny = dy / length
    
    // Смещение от границы узла
    const offset = 20
    const adjustedFromX = fromPos.x + nx * offset
    const adjustedFromY = fromPos.y + ny * offset
    const adjustedToX = toPos.x - nx * offset
    const adjustedToY = toPos.y - ny * offset
    
    const markerId = `arrow-${color.replace('#', '')}`
    
    if (smooth.enabled && smooth.type === 'cubicBezier') {
      // Кривая Безье
      const { cp1x, cp1y, cp2x, cp2y } = this._calculateBezierPoints(
        { x: adjustedFromX, y: adjustedFromY },
        { x: adjustedToX, y: adjustedToY },
        smooth.roundness,
        smooth.forceDirection
      )
      
      return `
        <path
          d="M ${adjustedFromX},${adjustedFromY} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${adjustedToX},${adjustedToY}"
          stroke="${color}"
          stroke-width="${width}"
          stroke-dasharray="${dashes}"
          fill="none"
          marker-end="url(#${markerId})"
        />
      `
    } else {
      // Прямая линия
      return `
        <line
          x1="${adjustedFromX}"
          y1="${adjustedFromY}"
          x2="${adjustedToX}"
          y2="${adjustedToY}"
          stroke="${color}"
          stroke-width="${width}"
          stroke-dasharray="${dashes}"
          marker-end="url(#${markerId})"
        />
      `
    }
  }
  
  _calculateBezierPoints(fromPos, toPos, roundness, forceDirection) {
    const dx = toPos.x - fromPos.x
    const dy = toPos.y - fromPos.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    let cp1x, cp1y, cp2x, cp2y
    
    if (forceDirection === 'vertical') {
      const midX = (fromPos.x + toPos.x) / 2
      const controlOffset = distance * roundness * 0.5
      
      if (dy > 0) {
        cp1x = midX
        cp1y = fromPos.y + controlOffset
        cp2x = midX
        cp2y = toPos.y - controlOffset
      } else {
        cp1x = midX
        cp1y = fromPos.y - controlOffset
        cp2x = midX
        cp2y = toPos.y + controlOffset
      }
    } else {
      const midY = (fromPos.y + toPos.y) / 2
      const controlOffset = distance * roundness * 0.5
      
      if (dx > 0) {
        cp1x = fromPos.x + controlOffset
        cp1y = midY
        cp2x = toPos.x - controlOffset
        cp2y = midY
      } else {
        cp1x = fromPos.x - controlOffset
        cp1y = midY
        cp2x = toPos.x + controlOffset
        cp2y = midY
      }
    }
    
    return { cp1x, cp1y, cp2x, cp2y }
  }
  
  // === Сериализация ===
  
  toDict() {
    return {
      ...super.toDict(),
      from_id: this.fromId,
      to_id: this.toId,
      type: this.type,
      projects: this.projects
    }
  }
  
  static fromDict(data) {
    return new GraphEdge(
      data.id,
      data.from_id || data.from,
      data.to_id || data.to,
      data.type || 'uses',
      data.projects || []
    )
  }
  
  validate() {
    if (!super.validate()) return false
    if (!this.fromId || !this.toId) return false
    return true
  }
}
```

---

## VisualizationManager

**Файл**: `src/lib/graph_viewer/frontend/src/services/VisualizationManager.js`

```javascript
import visualizationConfig from '@/config/visualization.json'
import { GraphVertex } from '../models/vertices/GraphVertex.js'
import { ConceptVertex } from '../models/vertices/ConceptVertex.js'
import { TechnologyVertex } from '../models/vertices/TechnologyVertex.js'
import { VersionVertex } from '../models/vertices/VersionVertex.js'
import { GraphEdge } from '../models/edges/GraphEdge.js'

export class VisualizationManager {
  constructor() {
    this.config = visualizationConfig
  }
  
  // === Фабрика объектов ===
  
  createVertex(id, key, label, properties = {}) {
    const type = this._inferVertexType(key)
    
    switch (type) {
      case 'concept':
        return new ConceptVertex(id, key, label, properties)
      case 'technology':
        return new TechnologyVertex(id, key, label, properties)
      case 'version':
        return new VersionVertex(id, key, label, properties)
      default:
        return new GraphVertex(id, key, label, properties)
    }
  }
  
  createEdge(id, fromId, toId, type = 'uses', projects = []) {
    return new GraphEdge(id, fromId, toId, type, projects)
  }
  
  _inferVertexType(key) {
    if (key.startsWith('c:')) return 'concept'
    if (key.startsWith('t:')) return 'technology'
    if (key.startsWith('v:')) return 'version'
    return 'default'
  }
  
  // === Опции для vis-network ===
  
  getVisNetworkOptions(theme) {
    // Только статичные опции (не цвета)
    return {
      layout: this.config.layout || {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 140,
          nodeSpacing: 180,
          treeSpacing: 240
        }
      },
      physics: this.config.physics || {
        enabled: true,
        solver: 'hierarchicalRepulsion',
        hierarchicalRepulsion: {
          nodeDistance: 160,
          springLength: 160,
          damping: 0.45,
          avoidOverlap: 1
        }
      },
      interaction: this.config.interaction || {
        hover: true,
        multiselect: true,
        zoomView: true,
        dragView: true
      },
      edges: {
        arrows: {
          to: { enabled: true, scaleFactor: 0.5 }
        },
        smooth: {
          enabled: true,
          type: 'cubicBezier',
          forceDirection: 'vertical',
          roundness: 0.5
        }
      }
    }
  }
  
  // === Применение темы к канве ===
  
  applyCanvasTheme(theme) {
    const canvasConfig = this.config.canvas ? this.config.canvas[theme] : null
    if (canvasConfig && canvasConfig.background) {
      const canvasElement = document.getElementById('graph')
      if (canvasElement) {
        canvasElement.style.backgroundColor = canvasConfig.background
      }
    }
  }
}
```

---

## Использование

### В store

**Файл**: `src/lib/graph_viewer/frontend/src/stores/graph.js`

```javascript
import { VisualizationManager } from '../services/VisualizationManager.js'

const vizManager = new VisualizationManager()

export const useGraphStore = defineStore('graph', () => {
  const network = ref(null)
  const nodesDataSet = ref(null)
  const edgesDataSet = ref(null)
  const theme = ref('light')
  
  // Загрузить граф
  const loadGraph = async (projectKey) => {
    const response = await fetch(`/api/graph?project=${projectKey}&theme=${theme.value}`)
    const data = await response.json()
    
    // Создать объекты через фабрику
    const vertices = data.nodes.map(n => 
      vizManager.createVertex(n.id, n.key, n.label, n.properties)
    )
    
    const edges = data.edges.map(e =>
      vizManager.createEdge(e.id, e.from, e.to, e.type, e.projects)
    )
    
    // Преобразовать для vis-network
    const visNodes = vertices.map(v => v.toVisNetworkFormat(theme.value))
    const visEdges = edges.map(e => {
      const fromPos = network.value.getPosition(e.fromId)
      const toPos = network.value.getPosition(e.toId)
      return e.toVisNetworkFormat(theme.value)
    })
    
    nodesDataSet.value.update(visNodes)
    edgesDataSet.value.update(visEdges)
  }
  
  // Применить тему (упрощённая версия)  const applyTheme = () => {
    if (!network.value) return
    
    // Применить тему к канве
    vizManager.applyCanvasTheme(theme.value)
    
    // Обновить узлы и рёбра через объекты
    // (вместо прямого вызова setOptions)
    // Узлы и рёбра уже имеют правильные стили из toVisNetworkFormat()
  }
  
  return {
    loadGraph,
    applyTheme,
    // ...
  }
})
```

---

## Преимущества подхода

✅ **Единая точка правды**: `visualization.json` + классы  
✅ **Консистентность**: Canvas и SVG используют одни и те же классы  
✅ **Расширяемость**: Легко добавить новые типы узлов/рёбер  
✅ **Тестируемость**: Классы можно тестировать изолированно  
✅ **Поддерживаемость**: Логика централизована  
✅ **Type Safety**: Можно добавить TypeScript позже  

---

## Сравнение: До и После

### До (текущее состояние)

**Проблемы**:
- Стили в трёх местах: `visualization.json`, `GraphCanvas.vue`, `graph.js`
- Canvas и SVG выглядят по-разному
- Сложно поддерживать консистентность
- Дублирование кода рендеринга

**Код**:
```javascript
// В graph.js - хардкод
network.setOptions({
  nodes: {
    color: { background: '#ffffff', border: '#e0e0e0' },
    font: { color: '#000000', size: 12 }
  }
})

// В exportToSVG.js - свой подход
const color = node.color || '#ffffff'
const border = node.border || '#e0e0e0'
```

### После (с классами)

**Решения**:
- Один источник стилей: `visualization.json`
- Классы инкапсулируют логику рендеринга
- Canvas и SVG используют одни классы
- Нет дублирования

**Код**:
```javascript
// Создать объект
const vertex = vizManager.createVertex(id, key, label, props)

// Для canvas
const visNode = vertex.toVisNetworkFormat(theme)
nodesDataSet.update([visNode])

// Для SVG
const svg = vertex.toSVGFormat(theme, position)
```

---

## План миграции

### Шаг 1: Создать структуру
```bash
mkdir -p src/lib/graph_viewer/frontend/src/models/{vertices,edges,business}
mkdir -p src/lib/graph_viewer/frontend/src/services
mkdir -p src/lib/graph_viewer/frontend/src/renderers
```

### Шаг 2: Реализовать базовые классы
- [ ] `models/base.js` (GraphObject)
- [ ] `models/vertices/GraphVertex.js`
- [ ] `models/vertices/ConceptVertex.js`
- [ ] `models/vertices/TechnologyVertex.js`
- [ ] `models/vertices/VersionVertex.js`
- [ ] `models/edges/GraphEdge.js`

### Шаг 3: Реализовать сервисы
- [ ] `services/VisualizationManager.js`
- [ ] `services/GraphRepository.js`

### Шаг 4: Обновить существующий код
- [ ] `stores/graph.js` — использовать VisualizationManager
- [ ] `utils/exportToSVG.js` — использовать методы классов
- [ ] `components/GraphCanvas.vue` — убрать хардкод

### Шаг 5: Расширить конфиг
- [ ] Добавить в `visualization.json`:
  - `canvas` (фон)
  - `layout` (раскладка)
  - `physics` (физика)
  - `interaction` (взаимодействие)

### Шаг 6: Тестирование
- [ ] Проверить canvas
- [ ] Проверить SVG экспорт
- [ ] Проверить темы (dark/light)
- [ ] Проверить интерактивность (hover, selected)

---

## Дальнейшее развитие

### Этап 1: Базовая иерархия (текущий документ)
- Классы на фронтенде
- Единая визуализация

### Этап 2: Синхронизация с бакендом
- Классы на бакенде (Python)
- Общая схема данных
- Генераторы кода

### Этап 3: Метаданные в графе (финальное)
- Определения классов в графе
- `graph_traverse_down` с метаданными
- MCP команды для работы с классами
- Генератор из графа

См. [`metadata-in-graph-architecture.md`](./metadata-in-graph-architecture.md)

---

## Связанные документы

- [`chat-2025-11-04-svg-export-fixes-and-architecture-proposal.md`](./chat-2025-11-04-svg-export-fixes-and-architecture-proposal.md) — общее резюме
- [`metadata-in-graph-architecture.md`](./metadata-in-graph-architecture.md) — финальная архитектура
- [`frontend-backend-class-sync.md`](./frontend-backend-class-sync.md) — синхронизация

---

**Дата создания**: 2025-11-04  
**Автор**: Александр  
**Статус**: Предложение (часть общей архитектуры)  
**Версия**: 1.0
