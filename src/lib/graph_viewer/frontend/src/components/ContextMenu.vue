<template>
  <div 
    v-if="visible" 
    class="context-menu"
    :style="{ top: position.y + 'px', left: position.x + 'px' }"
    @click.stop
  >
    <!-- Меню для узлов -->
    <template v-if="nodeId">
      <div class="menu-section">
        <div class="menu-header">📊 Показать</div>
        <div class="menu-item" @click="handleExpandChildren">
          <span class="menu-icon">⬇️</span>
          <span class="menu-label">Нижестоящие (1 уровень)</span>
        </div>
        <div class="menu-item" @click="handleExpandParents">
          <span class="menu-icon">⬆️</span>
          <span class="menu-label">Вышестоящие (1 уровень)</span>
        </div>
      </div>
      
      <div class="menu-divider"></div>
      
      <div class="menu-section">
        <div class="menu-header">👁️‍🗨️ Скрыть</div>
        <div class="menu-item" @click="handleHideWithChildren">
          <span class="menu-icon">⬇️</span>
          <span class="menu-label">С нижестоящими (рекурсия)</span>
        </div>
        <div class="menu-item" @click="handleHideWithParents">
          <span class="menu-icon">⬆️</span>
          <span class="menu-label">С вышестоящими (рекурсия)</span>
        </div>
      </div>
      
      <div class="menu-divider"></div>
      
      <div class="menu-section">
        <div class="menu-item" @click="handleShowDetails">
          <span class="menu-icon">🔍</span>
          <span class="menu-label">Показать детали</span>
        </div>
        <div class="menu-item" @click="handleFocusNode">
          <span class="menu-icon">🎯</span>
          <span class="menu-label">Центрировать</span>
        </div>
      </div>
    </template>
    
    <!-- Меню для рёбер -->
    <template v-else-if="edgeId">
      <div class="menu-section">
        <div class="menu-item" @click="handleShowEdgeDetails">
          <span class="menu-icon">🔍</span>
          <span class="menu-label">Показать детали</span>
        </div>
      </div>
    </template>
    
    <!-- Меню для пустого места (экспорт графа) -->
    <template v-else>
      <div class="menu-section">
        <div class="menu-item" @click="handleExportToSVG">
          <span class="menu-icon">📄</span>
          <span class="menu-label">Экспорт в SVG</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { exportGraphToSVG, downloadSVG } from '@/utils/exportToSVG'

const store = useGraphStore()

// Props
const props = defineProps({
  nodeId: {
    type: String,
    default: ''
  },
  edgeId: {
    type: String,
    default: ''
  },
  visible: {
    type: Boolean,
    default: false
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 })
  }
})

// Emits
const emit = defineEmits(['close'])

/**
 * Обработчик: Показать нижестоящие
 */
const handleExpandChildren = async () => {
  if (!props.nodeId) return
  
  await store.expandNodeChildren(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Показать вышестоящие
 */
const handleExpandParents = async () => {
  if (!props.nodeId) return
  
  await store.expandNodeParents(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Скрыть с нижестоящими
 */
const handleHideWithChildren = async () => {
  if (!props.nodeId) return
  
  await store.hideNodeWithChildren(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Скрыть с вышестоящими
 */
const handleHideWithParents = async () => {
  if (!props.nodeId) return
  
  await store.hideNodeWithParents(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Показать детали узла
 */
const handleShowDetails = async () => {
  if (!props.nodeId) return
  
  await store.selectNode(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Показать детали ребра
 */
const handleShowEdgeDetails = async () => {
  if (!props.edgeId) return
  
  await store.selectEdge(props.edgeId)
  emit('close')
}

/**
 * Обработчик: Центрировать узел
 */
const handleFocusNode = () => {
  if (!props.nodeId) return
  
  store.focusNode(props.nodeId)
  emit('close')
}

/**
 * Обработчик: Экспорт графа в SVG
 */
const handleExportToSVG = () => {
  try {
    const network = store.network
    const nodesDataSet = store.nodesDataSet
    const edgesDataSet = store.edgesDataSet
    
    if (!network || !nodesDataSet || !edgesDataSet) {
      console.error('Cannot export: network not initialized')
      return
    }
    
    const theme = store.theme || 'light'
    const svgContent = exportGraphToSVG(network, nodesDataSet, edgesDataSet, theme)
    
    if (!svgContent) {
      console.error('Failed to generate SVG')
      return
    }
    
    downloadSVG(svgContent, 'graph.svg')
    console.log('Graph exported to SVG')
    
    emit('close')
  } catch (err) {
    console.error('Error exporting to SVG:', err)
  }
}

/**
 * Закрыть меню при клике вне его
 */
const handleClickOutside = (event) => {
  if (props.visible) {
    emit('close')
  }
}

// Lifecycle hooks
onMounted(() => {
  // Добавить обработчик на документ с небольшой задержкой
  // чтобы избежать закрытия меню сразу после открытия
  setTimeout(() => {
    document.addEventListener('click', handleClickOutside)
    // НЕ добавляем обработчик contextmenu, так как он закрывает меню сразу
  }, 100)
})

onUnmounted(() => {
  // Удалить обработчик
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  min-width: 240px;
  background: var(--bg-primary, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 10000;
  padding: 4px 0;
  font-size: 13px;
  user-select: none;
}

.menu-section {
  padding: 4px 0;
}

.menu-header {
  padding: 8px 12px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary, #999);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  color: var(--text-primary, #e0e0e0);
  transition: background 0.15s ease;
}

.menu-item:hover {
  background: var(--hover-bg, #2d3748);
}

.menu-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.menu-label {
  flex: 1;
  line-height: 1.4;
}

.menu-divider {
  height: 1px;
  background: var(--border-color, #444);
  margin: 4px 0;
}

/* Адаптация для светлой темы */
:global(.theme-light) .context-menu {
  background: var(--bg-primary, #ffffff);
  border-color: var(--border-color, #cbd5e0);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:global(.theme-light) .menu-header {
  color: var(--text-tertiary, #757575);
}

:global(.theme-light) .menu-item {
  color: var(--text-primary, #212121);
}

:global(.theme-light) .menu-item:hover {
  background: var(--hover-bg, #e8f4fd);
}

:global(.theme-light) .menu-divider {
  background: var(--border-color, #cbd5e0);
}
</style>

