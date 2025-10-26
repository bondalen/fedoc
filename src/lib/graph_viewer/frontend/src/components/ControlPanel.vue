<template>
  <div id="controls">
    <h3>🎛️ Управление графом</h3>
    
    <!-- Стартовая вершина -->
    <div class="row">
      <label>Стартовая вершина:</label>
      <select 
        v-model="store.startNode" 
        @change="onStartNodeChange"
        :disabled="store.isLoading"
      >
        <option 
          v-for="node in store.nodes" 
          :key="node._id" 
          :value="node._key"
        >
          {{ node._key }} - {{ node.name || 'Без имени' }}
        </option>
      </select>
    </div>
    
    <!-- Глубина обхода -->
    <div class="row">
      <label>
        Глубина обхода: 
        <span class="value-display">{{ store.depth }}</span>
      </label>
      <input 
        type="range" 
        v-model.number="store.depth" 
        min="1" 
        max="15" 
        @change="onDepthChange"
        :disabled="store.isLoading"
      />
    </div>
    
    <!-- Проект -->
    <div class="row">
      <label>Проект:</label>
      <select 
        v-model="store.project" 
        @change="onProjectChange"
        :disabled="store.isLoading"
      >
        <option value="">Все проекты</option>
        <option value="fepro">FEPRO</option>
        <option value="femsq">FEMSQ</option>
        <option value="fedoc">FEDOC</option>
      </select>
    </div>
    
    <!-- Тема -->
    <div class="row theme-row">
      <label>Тема:</label>
      <div class="theme-options">
        <label class="theme-option">
          <input 
            type="radio" 
            v-model="store.theme" 
            value="dark" 
            @change="onThemeChange"
          />
          <span>🌙 Тёмная</span>
        </label>
        <label class="theme-option">
          <input 
            type="radio" 
            v-model="store.theme" 
            value="light" 
            @change="onThemeChange"
          />
          <span>☀️ Светлая</span>
        </label>
      </div>
    </div>
    
    <!-- Кнопки действий -->
    <div class="row buttons">
      <button 
        @click="onRefresh" 
        class="btn-primary"
        :disabled="store.isLoading"
      >
        <span class="button-icon">{{ store.isLoading ? '⏳' : '🔄' }}</span>
        <span class="button-text">{{ store.isLoading ? 'Загрузка...' : 'Обновить' }}</span>
      </button>
      <button 
        @click="onFit" 
        class="btn-success"
        :disabled="store.isLoading || store.nodeCount === 0"
      >
        <span class="button-icon">📐</span>
        <span class="button-text">Подогнать</span>
      </button>
      
      <!-- НОВЫЕ КНОПКИ -->
      <button 
        @click="onShowAll" 
        class="btn-info"
        :disabled="store.isLoading"
      >
        <span class="button-icon">🌐</span>
        <span class="button-text">Показать всё</span>
      </button>
      <button 
        @click="onUndoView" 
        class="btn-warning"
        :disabled="!store.canUndo"
      >
        <span class="button-icon">↶</span>
        <span class="button-text">Отменить</span>
      </button>
      <button 
        @click="onRedoView" 
        class="btn-warning"
        :disabled="!store.canRedo"
      >
        <span class="button-icon">↷</span>
        <span class="button-text">Вернуть</span>
      </button>
    </div>
    
    <!-- Статистика -->
    <div class="stats">
      <div class="stats-row">
        <span class="stats-label">Узлов:</span>
        <span class="stats-value">{{ store.nodeCount }}</span>
      </div>
      <div class="stats-row">
        <span class="stats-label">Рёбер:</span>
        <span class="stats-value">{{ store.edgeCount }}</span>
      </div>
    </div>
    
    <!-- Индикатор истории -->
    <div class="history-indicator" v-if="store.viewHistory.length > 1">
      История: {{ store.currentHistoryIndex + 1 }}/{{ store.viewHistory.length }}
    </div>
    
    <!-- Ошибки -->
    <div v-if="store.error" class="error-message">
      ⚠️ {{ store.error }}
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()

/**
 * Обработчики событий
 */
const onStartNodeChange = () => {
  store.loadGraph()
}

const onDepthChange = () => {
  // Загружать граф всегда, независимо от наличия стартового узла
  store.loadGraph()
}

const onProjectChange = () => {
  store.changeProject()
}

const onThemeChange = () => {
  store.applyTheme()
  // Применить тему к body
  document.body.className = store.theme
}

const onRefresh = () => {
  store.loadGraph()
  // 🎯 ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ТЕМЫ после загрузки
  setTimeout(() => {
    store.applyTheme()
  }, 500)
}

const onFit = () => {
  store.fitGraph()
}

const onShowAll = () => {
  store.showAllGraph()
}

const onUndoView = () => {
  store.undoView()
}

const onRedoView = () => {
  store.redoView()
}

// Адаптивное скрытие текста кнопок при недостаточной ширине
const checkButtonWidths = () => {
  const buttonContainer = document.querySelector('.row.buttons')
  if (!buttonContainer) return
  
  const containerWidth = buttonContainer.offsetWidth
  const buttons = document.querySelectorAll('.row.buttons button')
  const buttonCount = buttons.length
  
  // Вычислить доступную ширину на кнопку
  const availableWidthPerButton = (containerWidth - (buttonCount - 1) * 4) / buttonCount // 4px gap
  
  buttons.forEach(button => {
    const text = button.querySelector('.button-text')
    const icon = button.querySelector('.button-icon')
    
    if (text && icon) {
      // Скрыть текст если ширина кнопки меньше 50px
      if (availableWidthPerButton < 50) {
        text.style.display = 'none'
        icon.style.marginBottom = '0'
      } else {
        text.style.display = 'block'
        icon.style.marginBottom = '2px'
      }
    }
  })
}

// Проверка при изменении размера окна
onMounted(() => {
  // Проверить после небольшой задержки, чтобы DOM был готов
  setTimeout(() => {
    checkButtonWidths()
  }, 100)
  
  window.addEventListener('resize', checkButtonWidths)
  
  // Проверить при изменении данных графа
  const interval = setInterval(checkButtonWidths, 1000)
  
  onUnmounted(() => {
    clearInterval(interval)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', checkButtonWidths)
})
</script>

<style scoped>
#controls {
  position: fixed;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 15px;
  border-radius: 8px;
  z-index: 1000;
  min-width: 280px;
  max-width: 320px;
  backdrop-filter: blur(10px);
  max-height: 90vh;
  overflow-y: auto;
}

h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
}

.row {
  margin-bottom: 12px;
}

.row label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: bold;
  color: #e0e0e0;
}

.value-display {
  float: right;
  color: #64B5F6;
  font-weight: bold;
}

.row select,
.row input[type="range"] {
  width: 100%;
  padding: 6px;
  border: 1px solid #444;
  background: #2d3748;
  color: #e0e0e0;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.row select:disabled,
.row input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.row select:hover:not(:disabled),
.row input[type="range"]:hover:not(:disabled) {
  border-color: #64B5F6;
}

.row input[type="range"] {
  cursor: pointer;
  width: 100%;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.theme-row label {
  margin-bottom: 8px;
}

.theme-options {
  display: flex;
  gap: 8px;
}

.theme-option {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: #2d3748;
  border: 1px solid #444;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: normal;
  margin-bottom: 0;
}

.theme-option:hover {
  background: #3a4a5e;
  border-color: #64B5F6;
}

.theme-option input[type="radio"] {
  margin: 0;
  cursor: pointer;
}

.theme-option span {
  font-size: 11px;
}

.row.buttons {
  display: flex;
  gap: 4px;
  margin-top: 15px;
  max-width: 100%;
  overflow: hidden;
}

button {
  padding: 6px 4px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  flex: 1;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 32px;
  min-width: 0;
  position: relative;
}

/* Адаптивное скрытие текста при недостаточной ширине */
.row.buttons button .button-text {
  transition: opacity 0.2s ease;
}

/* При узкой панели - скрыть текст, оставить только иконки */
@media (max-width: 350px) {
  .row.buttons button .button-text {
    display: none;
  }
  
  .row.buttons button {
    padding: 4px 2px;
  }
}

/* При очень узкой панели - уменьшить иконки */
@media (max-width: 280px) {
  .row.buttons {
    gap: 2px;
  }
  
  .row.buttons button {
    padding: 2px 1px;
  }
  
  .row.buttons button .button-icon {
    font-size: 12px;
  }
}

.row.buttons button .button-icon {
  font-size: 14px;
  line-height: 1;
  margin-bottom: 2px;
}

.row.buttons button .button-text {
  font-size: 9px;
  margin-top: 2px;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  text-align: center;
}

/* Принудительное выравнивание всех кнопок */
.row.buttons {
  justify-content: space-between;
}

.row.buttons button {
  flex: 1 1 0;
  max-width: calc(20% - 2px);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #1976D2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1565C0;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);
}

.btn-success {
  background: #43A047;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #388E3C;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(67, 160, 71, 0.3);
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #138496;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(23, 162, 184, 0.3);
}

.btn-warning {
  background: #ffc107;
  color: #212529;
}

.btn-warning:hover:not(:disabled) {
  background: #e0a800;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.3);
}

.btn-warning:disabled {
  background: #6c757d;
  color: #fff;
  opacity: 0.5;
}

.stats {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #444;
  font-size: 11px;
  color: #ccc;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.stats-label {
  color: #999;
}

.stats-value {
  color: #64B5F6;
  font-weight: bold;
}

.error-message {
  margin-top: 12px;
  padding: 8px;
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.3);
  border-radius: 4px;
  color: #ff6b6b;
  font-size: 11px;
  line-height: 1.4;
}

/* Индикатор истории */
.history-indicator {
  margin-top: 8px;
  padding: 4px 8px;
  background: rgba(108, 117, 125, 0.1);
  border-radius: 4px;
  font-size: 10px;
  color: #6c757d;
}
</style>

