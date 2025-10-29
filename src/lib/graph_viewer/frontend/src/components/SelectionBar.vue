<template>
  <div class="selection-bar" v-if="store.selectionCount > 0">
    <div class="selection-header">
      <span class="selection-icon">📋</span>
      <span class="selection-title">Выбрано для Cursor AI</span>
      <span class="selection-count">({{ store.selectionCount }} объектов)</span>
    </div>
    
    <div class="selection-items">
      <!-- Узлы -->
      <div
        v-for="node in store.selectedNodesList"
        :key="node._id || node.id"
        class="selection-chip node-chip"
        :class="getNodeClass(node)"
        :title="getNodeTooltip(node)"
      >
        <span class="chip-icon">📦</span>
        <span class="chip-label">{{ getNodeLabel(node) }}</span>
      </div>
      
      <!-- Рёбра -->
      <div
        v-for="edge in store.selectedEdgesList"
        :key="edge._id"
        class="selection-chip edge-chip"
        :title="getEdgeTooltip(edge)"
      >
        <span class="chip-icon">🔗</span>
        <span class="chip-label">{{ getEdgeLabel(edge) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()

/**
 * Определить CSS класс для узла по его типу
 */
const getNodeClass = (node) => {
  const kind = node.kind || 'unknown'
  
  switch (kind) {
    case 'concept':
      return 'chip-concept'
    case 'technology':
      return 'chip-technology'
    case 'artifact':
      return 'chip-artifact'
    default:
      return 'chip-default'
  }
}

/**
 * Получить тултип для узла
 */
const getNodeTooltip = (node) => {
  const parts = []
  
  if (node._id) parts.push(`ID: ${node._id}`)
  if (node._key) parts.push(`Key: ${node._key}`)
  if (node.kind) parts.push(`Тип: ${node.kind}`)
  if (node.description) parts.push(`Описание: ${node.description.substring(0, 100)}...`)
  
  return parts.join('\n')
}

/**
 * Получить метку для узла
 */
const getNodeLabel = (node) => {
  // Приоритет: arango_key > name > _key > id
  if (node.properties && node.properties.arango_key) {
    return node.properties.arango_key
  }
  if (node.arango_key) {
    return node.arango_key
  }
  if (node.name) {
    return node.name
  }
  if (node._key) {
    return node._key
  }
  return node._id || node.id || '?'
}

/**
 * Получить метку для ребра
 */
const getEdgeLabel = (edge) => {
  let fromName = '?'
  let toName = '?'
  
  if (edge._from) {
    // ArangoDB формат
    fromName = edge._from.split('/').pop()
  } else if (edge.start_id) {
    // PostgreSQL+AGE формат - ищем arango_key узла
    fromName = getNodeArangoKeyById(edge.start_id)
  }
  
  if (edge._to) {
    // ArangoDB формат
    toName = edge._to.split('/').pop()
  } else if (edge.end_id) {
    // PostgreSQL+AGE формат - ищем arango_key узла
    toName = getNodeArangoKeyById(edge.end_id)
  }
  
  return `${fromName} → ${toName}`
}

/**
 * Получить arango_key узла по его ID
 */
const getNodeArangoKeyById = (nodeId) => {
  // Ищем в разных источниках данных
  let node = null
  const idNum = Number(nodeId)
  const idStr = String(nodeId)

  // 1. В актуальном DataSet (vis-network)
  if (store.nodesDataSet) {
    const dsByNum = store.nodesDataSet.get(idNum)
    const dsByStr = store.nodesDataSet.get(idStr)
    node = dsByNum || dsByStr || null
    if (node) {
      console.log(`Looking in nodesDataSet for nodeId: ${nodeId}, found:`, node)
    }
  }

  // 2. Если не найден, пробуем в текущем состоянии истории (кэш 10 состояний)
  if (!node && store.viewHistory && typeof store.currentHistoryIndex === 'number') {
    const state = store.viewHistory[store.currentHistoryIndex]
    if (state && Array.isArray(state.nodes)) {
      node = state.nodes.find(n => n.id == nodeId || n._id == nodeId) || null
      console.log(`Looking in viewHistory state for nodeId: ${nodeId}, found:`, node)
    }
  }

  // 3. В списке доступных узлов (может не содержать всех отображаемых)
  if (!node && Array.isArray(store.nodes)) {
    node = store.nodes.find(n => n.id == nodeId || n._id == nodeId) || null
    console.log(`Looking in nodes for nodeId: ${nodeId}, found:`, node)
  }
  
  if (node) {
    // Проверяем разные возможные структуры данных - ПРИОРИТЕТ: _key (arango_key)
    if (node._key) {
      console.log(`Found _key:`, node._key)
      return node._key
    }
    if (node.properties && node.properties.arango_key) {
      console.log(`Found arango_key in properties:`, node.properties.arango_key)
      return node.properties.arango_key
    }
    if (node.arango_key) {
      console.log(`Found arango_key:`, node.arango_key)
      return node.arango_key
    }
    if (node.name) {
      console.log(`Found name:`, node.name)
      return node.name
    }
    if (node.label) {
      console.log(`Found label:`, node.label)
      return node.label
    }
  }
  
  // Если не найден, возвращаем ID
  console.log(`Node not found in any source, returning ID: #${nodeId}`)
  return `#${nodeId}`
}

/**
 * Получить тултип для ребра
 */
const getEdgeTooltip = (edge) => {
  const parts = []
  
  // Поддержка как ArangoDB, так и PostgreSQL+AGE форматов
  if (edge._id || edge.id) {
    parts.push(`ID: ${edge._id || edge.id}`)
  }
  
  if (edge._from) {
    parts.push(`От: ${edge._from}`)
  } else if (edge.start_id) {
    parts.push(`От: #${edge.start_id}`)
  }
  
  if (edge._to) {
    parts.push(`К: ${edge._to}`)
  } else if (edge.end_id) {
    parts.push(`К: #${edge.end_id}`)
  }
  
  // Проекты могут быть в properties
  const projects = edge.projects || (edge.properties && edge.properties.projects)
  if (projects && projects.length > 0) {
    parts.push(`Проекты: ${projects.join(', ')}`)
  }
  
  // Тип связи может быть в properties
  const relationType = edge.relationType || (edge.properties && edge.properties.relationType)
  if (relationType) {
    parts.push(`Тип связи: ${relationType}`)
  }
  
  return parts.join('\n')
}
</script>

<style scoped>
.selection-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--bg-secondary, #1a1a1a);
  border-top: 2px solid var(--border-color, #444);
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 0 12px;
  gap: 12px;
  z-index: 1000;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.3);
}

.selection-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding-right: 12px;
  border-right: 1px solid var(--border-color, #444);
  color: var(--text-secondary, #ccc);
  font-size: 13px;
}

.selection-icon {
  font-size: 16px;
}

.selection-title {
  font-weight: 500;
}

.selection-count {
  color: var(--text-tertiary, #999);
  font-size: 12px;
}

.selection-items {
  display: flex;
  flex-direction: row;
  gap: 8px;
  overflow-x: auto;
  overflow-y: hidden;
  flex: 1;
  padding: 8px 0;
  
  /* Кастомный скроллбар */
  scrollbar-width: thin;
  scrollbar-color: #555 transparent;
}

.selection-items::-webkit-scrollbar {
  height: 6px;
}

.selection-items::-webkit-scrollbar-track {
  background: transparent;
}

.selection-items::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.selection-items::-webkit-scrollbar-thumb:hover {
  background: #666;
}

.selection-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;
  cursor: default;
  user-select: none;
}

.chip-icon {
  font-size: 14px;
  line-height: 1;
}

.chip-label {
  font-weight: 500;
  line-height: 1;
}

/* Цветовая кодировка узлов */
.node-chip.chip-concept {
  background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
  color: white;
  border: 1px solid #0D47A1;
}

.node-chip.chip-technology {
  background: linear-gradient(135deg, #388E3C 0%, #2E7D32 100%);
  color: white;
  border: 1px solid #1B5E20;
}

.node-chip.chip-artifact {
  background: linear-gradient(135deg, #7B1FA2 0%, #6A1B9A 100%);
  color: white;
  border: 1px solid #4A148C;
}

.node-chip.chip-default {
  background: linear-gradient(135deg, #455A64 0%, #37474F 100%);
  color: white;
  border: 1px solid #263238;
}

/* Рёбра */
.edge-chip {
  background: linear-gradient(135deg, #F57C00 0%, #E65100 100%);
  color: white;
  border: 1px solid #BF360C;
}

/* Hover эффекты (хотя плашки не кликабельные) */
.selection-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

/* Адаптация для светлой темы */
:global(.theme-light) .selection-bar {
  background: var(--bg-primary, #ffffff);
  border-top-color: var(--border-color, #cbd5e0);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
}

:global(.theme-light) .selection-header {
  border-right-color: var(--border-color, #cbd5e0);
  color: var(--text-secondary, #424242);
}

:global(.theme-light) .selection-count {
  color: var(--text-tertiary, #757575);
}
</style>

