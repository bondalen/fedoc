<template>
  <div 
    id="fullTextPanel" 
    :class="{ visible: store.showFullText }"
  >
    <!-- Заголовок -->
    <div id="fullTextHeader">
      <h4>📄 Полный текст</h4>
      <button @click="onToggle" aria-label="Закрыть">✕</button>
    </div>
    
    <!-- Содержимое -->
    <div id="fullTextContent">
      <pre>{{ store.fullText || 'Нет текста для отображения' }}</pre>
    </div>
  </div>
</template>

<script setup>
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()

const onToggle = () => {
  store.toggleFullText()
}
</script>

<style scoped>
#fullTextPanel {
  position: fixed;
  bottom: -250px;
  left: 0;
  /* Останавливаемся на левой границе панели деталей (420px от правого края) */
  right: 420px;
  height: 250px;
  background: #1a1a1a;
  border-top: 2px solid #333;
  z-index: 998; /* Ниже панели деталей (z-index: 999) */
  display: flex;
  flex-direction: column;
  transition: bottom 0.3s ease;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.3);
}

#fullTextPanel.visible {
  bottom: 0;
}

#fullTextHeader {
  padding: 10px 15px;
  background: #252525;
  border-bottom: 1px solid #333;
  position: relative;
  flex-shrink: 0;
}

#fullTextHeader h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #ccc;
  padding-right: 30px;
}

#fullTextHeader button {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 14px;
  width: 20px;
  height: 20px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

#fullTextHeader button:hover {
  background: #444;
  color: #fff;
}

#fullTextContent {
  padding: 15px;
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
}

#fullTextContent pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 11px;
  line-height: 1.5;
  color: #e0e0e0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Scrollbar styling */
#fullTextContent::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

#fullTextContent::-webkit-scrollbar-track {
  background: #1a1a1a;
}

#fullTextContent::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

#fullTextContent::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>

