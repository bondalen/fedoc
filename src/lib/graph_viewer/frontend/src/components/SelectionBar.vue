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
        :key="node._id"
        class="selection-chip node-chip"
        :class="getNodeClass(node)"
        :title="getNodeTooltip(node)"
      >
        <span class="chip-icon">📦</span>
        <span class="chip-label">{{ node.name || node._key || node._id }}</span>
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
 * Получить метку для ребра
 */
const getEdgeLabel = (edge) => {
  // Попробовать получить названия узлов
  const fromName = edge._from ? edge._from.split('/').pop() : '?'
  const toName = edge._to ? edge._to.split('/').pop() : '?'
  
  return `${fromName} → ${toName}`
}

/**
 * Получить тултип для ребра
 */
const getEdgeTooltip = (edge) => {
  const parts = []
  
  if (edge._id) parts.push(`ID: ${edge._id}`)
  if (edge._from) parts.push(`От: ${edge._from}`)
  if (edge._to) parts.push(`К: ${edge._to}`)
  if (edge.projects && edge.projects.length > 0) {
    parts.push(`Проекты: ${edge.projects.join(', ')}`)
  }
  if (edge.relationType) parts.push(`Тип связи: ${edge.relationType}`)
  
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

