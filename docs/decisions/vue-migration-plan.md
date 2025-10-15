# План миграции Graph Viewer на Vue.js 3

**Дата начала:** 2025-10-15  
**Ветка:** `feature/vue-migration`  
**Статус:** 🚀 В процессе  

---

## 🎯 Цель миграции

Переход с Alpine.js на Vue.js 3 для:
- ✅ Полноценной компонентной архитектуры
- ✅ Лучшей масштабируемости
- ✅ Встроенной реактивности (Composition API)
- ✅ Более простого синтаксиса чем React
- ✅ Идеальной интеграции с Vite (созданы одним автором)

---

## 📦 Технологический стек

### Frontend Framework
- **Vue.js 3** - прогрессивный фреймворк
- **Composition API** - для логики компонентов
- **TypeScript** - типизация (опционально на старте)

### Сборка и Dev Server
- **Vite** - уже используется, минимальные изменения

### Библиотеки
- **vis-network** - визуализация графа (без изменений)
- **vis-data** - управление данными графа
- **Pinia** - state management (легче Vuex)

### UI компоненты (по необходимости)
- Можем использовать простые CSS (текущие стили)
- Или добавить UI библиотеку позже

---

## 🏗️ Архитектура Vue.js приложения

```
frontend/
├── public/
│   └── vite.svg
├── src/
│   ├── components/              # Vue компоненты
│   │   ├── GraphViewer.vue      # Главный компонент
│   │   ├── ControlPanel.vue     # Панель управления
│   │   ├── GraphCanvas.vue      # Холст с vis-network
│   │   ├── DetailsPanel.vue     # Панель деталей
│   │   ├── ObjectTree.vue       # Дерево объекта
│   │   ├── ObjectNode.vue       # Узел дерева
│   │   └── FullTextPanel.vue    # Панель полного текста
│   ├── composables/             # Переиспользуемая логика
│   │   ├── useGraph.js          # Логика работы с графом
│   │   ├── useApi.js            # API запросы
│   │   └── useTheme.js          # Управление темами
│   ├── stores/                  # Pinia stores
│   │   └── graph.js             # Глобальное состояние графа
│   ├── utils/                   # Утилиты
│   │   ├── formatters.js        # Форматирование данных
│   │   └── constants.js         # Константы
│   ├── assets/                  # Статические ресурсы
│   │   └── styles.css           # Глобальные стили
│   ├── App.vue                  # Корневой компонент
│   └── main.js                  # Точка входа
├── index.html
├── package.json
└── vite.config.js
```

---

## 📋 План миграции (поэтапно)

### Этап 1: Настройка проекта (30 мин - 1 час)

**Задачи:**
- [x] Создать ветку `feature/vue-migration`
- [ ] Переименовать `frontend/` в `frontend-alpine/` (бэкап)
- [ ] Создать новый Vue.js проект с Vite
- [ ] Установить зависимости
- [ ] Скопировать текущие стили
- [ ] Настроить API endpoint (без изменений)

**Команды:**
```bash
cd src/lib/graph_viewer
mv frontend frontend-alpine
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install vis-network vis-data pinia
```

---

### Этап 2: Базовые компоненты (1-2 часа)

#### 2.1. App.vue - Корневой компонент
```vue
<template>
  <div id="app" :class="theme">
    <GraphViewer />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import GraphViewer from './components/GraphViewer.vue'

const theme = ref('dark')
</script>
```

#### 2.2. GraphViewer.vue - Главный компонент
```vue
<template>
  <div class="graph-viewer">
    <ControlPanel />
    <GraphCanvas />
    <DetailsPanel v-if="showDetails" />
    <FullTextPanel v-if="showFullText" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGraphStore } from '@/stores/graph'
import ControlPanel from './ControlPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import DetailsPanel from './DetailsPanel.vue'
import FullTextPanel from './FullTextPanel.vue'

const store = useGraphStore()
const showDetails = ref(false)
const showFullText = ref(false)
</script>
```

#### 2.3. ControlPanel.vue - Панель управления
```vue
<template>
  <div id="controls">
    <h3>🎛️ Управление графом</h3>
    
    <div class="row">
      <label>Стартовая вершина:</label>
      <select v-model="store.startNode" @change="loadGraph">
        <option v-for="node in store.nodes" :key="node._id" :value="node._id">
          {{ node._key }} - {{ node.name }}
        </option>
      </select>
    </div>
    
    <div class="row">
      <label>Глубина обхода:</label>
      <input 
        type="range" 
        v-model="store.depth" 
        min="1" 
        max="15" 
        @change="loadGraph"
      />
      <span>{{ store.depth }}</span>
    </div>
    
    <div class="row">
      <label>Проект:</label>
      <select v-model="store.project" @change="onProjectChange">
        <option value="">Все проекты</option>
        <option value="fepro">FEPRO</option>
        <option value="femsq">FEMSQ</option>
        <option value="fedoc">FEDOC</option>
      </select>
    </div>
    
    <div class="row">
      <label>Тема:</label>
      <label><input type="radio" v-model="store.theme" value="dark" @change="applyTheme"> 🌙 Тёмная</label>
      <label><input type="radio" v-model="store.theme" value="light" @change="applyTheme"> ☀️ Светлая</label>
    </div>
    
    <div class="row buttons">
      <button @click="loadGraph" class="btn-primary">🔄 Обновить</button>
      <button @click="fitGraph" class="btn-success">📐 Подогнать</button>
    </div>
    
    <div class="stats">
      Узлов: {{ store.nodeCount }} • Рёбер: {{ store.edgeCount }}
    </div>
  </div>
</template>

<script setup>
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()

const loadGraph = () => store.loadGraph()
const fitGraph = () => store.fitGraph()
const applyTheme = () => store.applyTheme()
const onProjectChange = () => {
  store.loadNodes()
  store.loadGraph()
}
</script>
```

---

### Этап 3: Интеграция vis-network (1-2 часа)

#### 3.1. GraphCanvas.vue - Холст графа
```vue
<template>
  <div id="graph" ref="graphContainer"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()
const graphContainer = ref(null)
let network = null

onMounted(() => {
  initNetwork()
  store.loadNodes()
  store.loadGraph()
})

const initNetwork = () => {
  const options = {
    nodes: {
      shape: 'box',
      margin: 10,
      font: { size: 12, face: 'arial' }
    },
    edges: {
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
      smooth: { type: 'continuous' }
    },
    physics: {
      stabilization: { iterations: 100 },
      barnesHut: { gravitationalConstant: -8000, springLength: 150 }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200
    }
  }
  
  const nodesDataSet = new DataSet([])
  const edgesDataSet = new DataSet([])
  
  network = new Network(
    graphContainer.value,
    { nodes: nodesDataSet, edges: edgesDataSet },
    options
  )
  
  // Event listeners
  network.on('selectNode', (params) => {
    if (params.nodes.length > 0) {
      store.selectNode(params.nodes[0])
    }
  })
  
  network.on('selectEdge', (params) => {
    if (params.edges.length > 0) {
      store.selectEdge(params.edges[0])
    }
  })
  
  store.setNetwork(network, nodesDataSet, edgesDataSet)
}
</script>

<style scoped>
#graph {
  flex: 1;
  border: 1px solid #333;
  background: #1e1e1e;
}
</style>
```

---

### Этап 4: Панель деталей (2-3 часа)

#### 4.1. DetailsPanel.vue
```vue
<template>
  <div 
    id="detailsPanel" 
    :style="{ width: panelWidth + 'px' }"
  >
    <div id="detailsHeader">
      <h4>Детали объекта</h4>
      <button @click="close">✕</button>
    </div>
    
    <div id="detailsContent">
      <ObjectTree v-if="store.selectedObject" :object="store.selectedObject" />
    </div>
    
    <!-- Resizer -->
    <div 
      id="resizer" 
      @mousedown="startResize"
    ></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGraphStore } from '@/stores/graph'
import ObjectTree from './ObjectTree.vue'

const store = useGraphStore()
const panelWidth = ref(420)
const isResizing = ref(false)

const close = () => store.closeDetails()

const startResize = (e) => {
  isResizing.value = true
  document.addEventListener('mousemove', resize)
  document.addEventListener('mouseup', stopResize)
}

const resize = (e) => {
  if (isResizing.value) {
    const newWidth = window.innerWidth - e.clientX
    if (newWidth >= 300 && newWidth <= 800) {
      panelWidth.value = newWidth
    }
  }
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', resize)
  document.removeEventListener('mouseup', stopResize)
}
</script>
```

#### 4.2. ObjectTree.vue - Рекурсивное дерево
```vue
<template>
  <div class="object-tree">
    <div v-for="(value, key) in object" :key="key" class="tree-item">
      <ObjectNode 
        :name="key" 
        :value="value" 
        :path="key"
      />
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'
import ObjectNode from './ObjectNode.vue'

defineProps({
  object: Object
})
</script>
```

#### 4.3. ObjectNode.vue - Узел дерева
```vue
<template>
  <div class="node">
    <!-- Кнопка раскрытия для объектов/массивов -->
    <button 
      v-if="isExpandable" 
      @click="toggleCollapse"
      class="collapse-btn"
    >
      {{ isCollapsed ? '▶' : '▼' }}
    </button>
    
    <!-- Имя ключа -->
    <span class="key">{{ name }}:</span>
    
    <!-- Значение (строка, число, boolean) -->
    <span v-if="isPrimitive" :class="valueClass">
      {{ displayValue }}
    </span>
    
    <!-- Ссылка на документ -->
    <span v-else-if="isDocRef" class="doc-link" @click="expandDoc">
      {{ formattedDocId }}
    </span>
    
    <!-- Кнопка "Показать на графе" -->
    <button 
      v-if="isGraphNode" 
      @click="showOnGraph"
      class="show-on-graph-btn"
    >
      📍 Показать
    </button>
    
    <!-- Вложенный объект/массив -->
    <div v-if="isExpandable && !isCollapsed" class="nested">
      <ObjectNode 
        v-for="(v, k) in value" 
        :key="k"
        :name="k"
        :value="v"
        :path="`${path}.${k}`"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { formatDocumentId, isDocumentRef } from '@/utils/formatters'

const props = defineProps({
  name: [String, Number],
  value: null,
  path: String
})

const store = useGraphStore()
const isCollapsed = ref(true)

const isPrimitive = computed(() => {
  const type = typeof props.value
  return ['string', 'number', 'boolean'].includes(type) || props.value === null
})

const isExpandable = computed(() => {
  return typeof props.value === 'object' && props.value !== null
})

const isDocRef = computed(() => {
  return typeof props.value === 'string' && isDocumentRef(props.value)
})

const isGraphNode = computed(() => {
  return isDocRef.value && props.value.includes('canonical_nodes/')
})

const valueClass = computed(() => {
  const type = typeof props.value
  if (type === 'string') return 'json-string'
  if (type === 'number') return 'json-number'
  if (type === 'boolean') return 'json-boolean'
  if (props.value === null) return 'json-null'
  return ''
})

const displayValue = computed(() => {
  if (typeof props.value === 'string') {
    // Truncate long strings
    if (props.value.length > 100) {
      return `"${props.value.substring(0, 100)}..."`
    }
    return `"${props.value}"`
  }
  return String(props.value)
})

const formattedDocId = computed(() => {
  return formatDocumentId(props.value)
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const expandDoc = async () => {
  await store.loadDocumentDetails(props.value)
}

const showOnGraph = () => {
  store.focusNode(props.value)
}
</script>
```

---

### Этап 5: Pinia Store (1 час)

#### stores/graph.js
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_BASE = 'http://127.0.0.1:8899'

export const useGraphStore = defineStore('graph', () => {
  // State
  const nodes = ref([])
  const startNode = ref('')
  const depth = ref(5)
  const project = ref('')
  const theme = ref('dark')
  
  const network = ref(null)
  const nodesDataSet = ref(null)
  const edgesDataSet = ref(null)
  
  const selectedObject = ref(null)
  const showDetails = ref(false)
  const fullText = ref('')
  const showFullText = ref(false)
  
  const loadedDocs = ref(new Set())
  
  // Computed
  const nodeCount = computed(() => nodesDataSet.value?.length || 0)
  const edgeCount = computed(() => edgesDataSet.value?.length || 0)
  
  // Actions
  const setNetwork = (net, nodesDS, edgesDS) => {
    network.value = net
    nodesDataSet.value = nodesDS
    edgesDataSet.value = edgesDS
  }
  
  const loadNodes = async () => {
    const params = new URLSearchParams()
    if (project.value) params.append('project', project.value)
    
    const res = await fetch(`${API_BASE}/nodes?${params}`)
    const data = await res.json()
    nodes.value = data.nodes || []
    
    if (nodes.value.length > 0 && !startNode.value) {
      startNode.value = nodes.value[0]._id
    }
  }
  
  const loadGraph = async () => {
    if (!startNode.value) return
    
    const params = new URLSearchParams({
      start_node: startNode.value,
      depth: depth.value
    })
    if (project.value) params.append('project', project.value)
    
    const res = await fetch(`${API_BASE}/graph?${params}`)
    const data = await res.json()
    
    nodesDataSet.value.clear()
    edgesDataSet.value.clear()
    
    nodesDataSet.value.add(data.nodes || [])
    edgesDataSet.value.add(data.edges || [])
    
    applyTheme()
  }
  
  const selectNode = async (nodeId) => {
    await loadObjectDetails(nodeId)
    showDetails.value = true
  }
  
  const selectEdge = async (edgeId) => {
    await loadObjectDetails(edgeId)
    showDetails.value = true
  }
  
  const loadObjectDetails = async (objectId) => {
    const res = await fetch(`${API_BASE}/object_details?object_id=${objectId}`)
    const data = await res.json()
    selectedObject.value = data.object
  }
  
  const loadDocumentDetails = async (docId) => {
    if (loadedDocs.value.has(docId)) return
    
    const res = await fetch(`${API_BASE}/object_details?object_id=${docId}`)
    const data = await res.json()
    loadedDocs.value.add(docId)
    return data.object
  }
  
  const closeDetails = () => {
    showDetails.value = false
    selectedObject.value = null
  }
  
  const openFullText = (text) => {
    fullText.value = text
    showFullText.value = true
  }
  
  const closeFullText = () => {
    showFullText.value = false
  }
  
  const focusNode = (nodeId) => {
    if (network.value) {
      network.value.selectNodes([nodeId])
      network.value.focus(nodeId, {
        scale: 1.2,
        animation: { duration: 500, easingFunction: 'easeInOutQuad' }
      })
    }
  }
  
  const fitGraph = () => {
    if (network.value) {
      network.value.fit({ animation: { duration: 500 } })
    }
  }
  
  const applyTheme = () => {
    // Apply theme logic
  }
  
  return {
    // State
    nodes, startNode, depth, project, theme,
    network, nodesDataSet, edgesDataSet,
    selectedObject, showDetails,
    fullText, showFullText,
    loadedDocs,
    
    // Computed
    nodeCount, edgeCount,
    
    // Actions
    setNetwork, loadNodes, loadGraph,
    selectNode, selectEdge,
    loadObjectDetails, loadDocumentDetails,
    closeDetails, openFullText, closeFullText,
    focusNode, fitGraph, applyTheme
  }
})
```

---

### Этап 6: Утилиты и стили (30 мин - 1 час)

#### utils/formatters.js
```javascript
export const shortenCollectionName = (collName) => {
  if (collName.length <= 4) return collName
  return `${collName.substring(0, 3)}.${collName.charAt(collName.length - 1)}`
}

export const formatDocumentId = (docId) => {
  if (!docId || typeof docId !== 'string') return docId
  
  const parts = docId.split('/')
  if (parts.length !== 2) return docId
  
  const [collection, key] = parts
  const shortColl = shortenCollectionName(collection)
  return `${shortColl}/${key}`
}

export const isDocumentRef = (str) => {
  if (typeof str !== 'string') return false
  return /^[a-z_]+\/[a-z0-9:_-]+$/i.test(str)
}

export const escapeHtml = (text) => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}
```

---

### Этап 7: Тестирование (1 час)

**Проверка:**
- [ ] Граф отображается корректно
- [ ] Фильтрация по проекту работает
- [ ] Выбор стартовой вершины работает
- [ ] Изменение глубины обновляет граф
- [ ] Клик по узлу открывает панель деталей
- [ ] Клик по ребру открывает панель деталей
- [ ] Разворачивание объектов работает
- [ ] Ссылки на документы открываются
- [ ] Кнопка "Показать на графе" работает
- [ ] Сокращение имён коллекций корректно
- [ ] Resizable панель работает
- [ ] Панель полного текста работает
- [ ] Темы (светлая/тёмная) работают

---

## ⏱️ Оценка времени

| Этап | Время |
|------|-------|
| 1. Настройка проекта | 0.5-1 ч |
| 2. Базовые компоненты | 1-2 ч |
| 3. vis-network интеграция | 1-2 ч |
| 4. Панель деталей | 2-3 ч |
| 5. Pinia store | 1 ч |
| 6. Утилиты и стили | 0.5-1 ч |
| 7. Тестирование | 1 ч |
| **ИТОГО** | **7-11 часов** |

---

## 🎯 Преимущества Vue.js решения

✅ **Настоящие компоненты** - каждый файл `.vue` - независимый компонент  
✅ **Реактивность из коробки** - `ref()`, `computed()`, `watch()`  
✅ **Простой синтаксис** - проще React, мощнее Alpine.js  
✅ **Composition API** - удобная логика  
✅ **Pinia** - современный state management  
✅ **SFC (Single File Components)** - template + script + style в одном файле  
✅ **Vite** - минимальные изменения конфигурации  
✅ **Легкая миграция в будущем** - на TypeScript или другие инструменты  

---

## 📝 Следующие шаги

1. ✅ Создать ветку `feature/vue-migration`
2. [ ] Начать миграцию (Этап 1)
3. [ ] Постепенно переносить функционал (Этапы 2-6)
4. [ ] Протестировать (Этап 7)
5. [ ] Создать Pull Request для review
6. [ ] Merge в main после успешного тестирования

---

**Готовы начинать?** 🚀

