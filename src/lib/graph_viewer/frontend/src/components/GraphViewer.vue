<template>
  <div class="graph-viewer" :class="themeClass">
    <!-- Панель управления -->
    <ControlPanel />
    
    <!-- Холст с графом -->
    <GraphCanvas @show-context-menu="handleShowContextMenu" />
    
    <!-- Панель деталей (справа) -->
    <DetailsPanel />
    
    <!-- Панель полного текста (снизу) -->
    <FullTextPanel />
    
    <!-- Строка выборки для Cursor AI (самый низ) -->
    <SelectionBar />
    
    <!-- Контекстное меню -->
    <ContextMenu 
      :visible="contextMenu.visible"
      :node-id="contextMenu.nodeId"
      :edge-id="contextMenu.edgeId"
      :position="contextMenu.position"
      @close="handleCloseContextMenu"
    />
    
    <!-- Индикатор загрузки -->
    <div v-if="store.isLoading" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>Загрузка графа...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, onMounted, onUnmounted } from 'vue'
import { useGraphStore } from '@/stores/graph'
import ControlPanel from './ControlPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import DetailsPanel from './DetailsPanel.vue'
import FullTextPanel from './FullTextPanel.vue'
import SelectionBar from './SelectionBar.vue'
import ContextMenu from './ContextMenu.vue'

const store = useGraphStore()

const themeClass = computed(() => {
  return `theme-${store.theme}`
})

// Состояние контекстного меню
const contextMenu = reactive({
  visible: false,
  nodeId: '',
  edgeId: '',
  position: { x: 0, y: 0 }
})

/**
 * Показать контекстное меню
 */
const handleShowContextMenu = ({ nodeId, edgeId, position }) => {
  contextMenu.visible = true
  contextMenu.nodeId = nodeId ? String(nodeId) : ''
  contextMenu.edgeId = edgeId ? String(edgeId) : ''
  contextMenu.position = position
  
  if (nodeId) {
    console.log(`Show context menu for node: ${nodeId}`)
  } else if (edgeId) {
    console.log(`Show context menu for edge: ${edgeId}`)
  } else {
    console.log('Show context menu for empty canvas')
  }
}

/**
 * Закрыть контекстное меню
 */
const handleCloseContextMenu = () => {
  contextMenu.visible = false
  contextMenu.nodeId = ''
  contextMenu.edgeId = ''
  
  console.log('Context menu closed')
}

// Инициализация WebSocket при монтировании компонента
onMounted(() => {
  console.log('GraphViewer mounted, initializing WebSocket...')
  store.initWebSocket()
})

// Закрытие WebSocket при размонтировании
onUnmounted(() => {
  console.log('GraphViewer unmounted, closing WebSocket...')
  store.closeWebSocket()
})
</script>

<style scoped>
.graph-viewer {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  /* Фон будет задаваться через темы */
}

/* Темы */
.theme-dark {
  background: #111;
  color: #e0e0e0;
}

.theme-light {
  background: #f5f5f5;
  color: #333;
}

/* Глобальные стили для светлой темы */
:deep(.theme-light) {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --bg-tertiary: #e0e0e0;
  --text-primary: #212121;
  --text-secondary: #424242;
  --text-tertiary: #757575;
  --border-color: #cbd5e0;
  --hover-bg: #e8f4fd;
  --canvas-bg: #ffffff;
}

/* Глобальные стили для тёмной темы */
:deep(.theme-dark) {
  --bg-primary: #1a1a1a;
  --bg-secondary: #252525;
  --bg-tertiary: #333333;
  --text-primary: #e0e0e0;
  --text-secondary: #ccc;
  --text-tertiary: #999;
  --border-color: #444;
  --hover-bg: #2d3748;
  --canvas-bg: #1e1e1e;
}

/* Индикатор загрузки */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.loading-spinner {
  text-align: center;
  color: white;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 20px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: #64B5F6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-spinner p {
  margin: 0;
  font-size: 14px;
  color: #64B5F6;
}
</style>

