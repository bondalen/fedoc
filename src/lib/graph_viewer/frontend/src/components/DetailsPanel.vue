<template>
  <div 
    id="detailsPanel" 
    :class="{ visible: store.showDetails }"
    :style="{ width: panelWidth + 'px' }"
  >
    <!-- Заголовок -->
    <div id="detailsHeader">
      <h3>🔍 Детали объекта</h3>
      <button @click="onClose" aria-label="Закрыть">✕</button>
    </div>
    
    <!-- Содержимое -->
    <div id="detailsContent">
      <ObjectTree v-if="store.selectedObject" :object="store.selectedObject" />
      <div v-else class="no-data">
        Выберите узел или ребро на графе
      </div>
    </div>
    
    <!-- Resizer для изменения размера панели -->
    <div 
      id="resizer" 
      @mousedown="startResize"
      :class="{ visible: store.showDetails }"
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

/**
 * Закрыть панель деталей
 */
const onClose = () => {
  store.closeDetails()
}

/**
 * Изменение размера панели
 */
const startResize = (e) => {
  isResizing.value = true
  document.addEventListener('mousemove', resize)
  document.addEventListener('mouseup', stopResize)
  e.preventDefault()
}

const resize = (e) => {
  if (isResizing.value) {
    const newWidth = window.innerWidth - e.clientX
    // Ограничения по ширине
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

<style scoped>
#detailsPanel {
  position: fixed;
  right: -420px;
  top: 0;
  width: 420px;
  height: 100vh;
  background: #1a1a1a;
  border-left: 2px solid #333;
  z-index: 999;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  transition: right 0.3s ease;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.3);
}

#detailsPanel.visible {
  right: 0;
}

#detailsHeader {
  padding: 12px 15px;
  background: #252525;
  border-bottom: 1px solid #333;
  position: relative;
  flex-shrink: 0;
}

#detailsHeader h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
  padding-right: 30px;
}

#detailsHeader button {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  color: #999;
  width: 20px;
  height: 20px;
  font-size: 14px;
  border-radius: 3px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

#detailsHeader button:hover {
  background: #444;
  color: #fff;
}

#detailsContent {
  padding: 15px;
  flex: 1;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.8;
}

/* Стили ObjectTree теперь в ObjectNode.vue */

.no-data {
  color: #666;
  font-style: italic;
  text-align: center;
  padding: 40px 20px;
  font-size: 14px;
}

/* Resizer */
#resizer {
  position: fixed;
  right: -5px;
  top: 0;
  width: 5px;
  height: 100vh;
  background: transparent;
  cursor: ew-resize;
  z-index: 1001;
  transition: right 0.3s ease;
}

#resizer:hover {
  background: #64B5F6;
}

#resizer.visible {
  right: 420px;
}

/* Scrollbar styling */
#detailsContent::-webkit-scrollbar {
  width: 8px;
}

#detailsContent::-webkit-scrollbar-track {
  background: #1a1a1a;
}

#detailsContent::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

#detailsContent::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>

