import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import io from 'socket.io-client'
import { applyNodesVisualization, applyEdgesVisualization } from '@/utils/visualization'

const API_BASE = '/api'

export const useGraphStore = defineStore('graph', () => {
  // ========== STATE ==========

  // Список доступных узлов для выбора
  const nodes = ref([])

  // Параметры графа
  const startNode = ref('')
  const depth = ref(5)
  const project = ref('')
  const theme = ref('dark')

  // Vis-network объекты
  const network = ref(null)
  const nodesDataSet = ref(null)
  const edgesDataSet = ref(null)

  // Панель деталей
  const selectedObject = ref(null)
  const showDetails = ref(false)

  // Панель полного текста
  const fullText = ref('')
  const showFullText = ref(false)

  // Кэш загруженных документов
  const loadedDocs = ref(new Set())
  const documentCache = ref(new Map())

  // Выборка для отправки в Cursor AI
  const selectedNodesList = ref([])
  const selectedEdgesList = ref([])

  // WebSocket соединение
  let socket = null
  const isSocketConnected = ref(false)

  // НОВАЯ АРХИТЕКТУРА: История состояний (только 10 состояний)
  const viewHistory = ref([])           // Массив состояний
  const currentHistoryIndex = ref(-1)   // Текущий индекс в истории
  const maxHistorySize = 10            // Максимум состояний в истории
  const isRestoringFromHistory = ref(false) // Флаг для предотвращения сохранения при восстановлении

  // Статус загрузки
  const isLoading = ref(false)
  const error = ref(null)

  // Таймер для автоочистки ошибок
  let errorTimeout = null

  // ========== COMPUTED ==========

  const nodeCount = computed(() => {
    return nodesDataSet.value ? nodesDataSet.value.length : 0
  })

  const edgeCount = computed(() => {
    return edgesDataSet.value ? edgesDataSet.value.length : 0
  })

  const selectionCount = computed(() => {
    return selectedNodesList.value.length + selectedEdgesList.value.length
  })

  const selectedNodesCount = computed(() => {
    return selectedNodesList.value.length
  })

  const selectedEdgesCount = computed(() => {
    return selectedEdgesList.value.length
  })

  const canUndo = computed(() => currentHistoryIndex.value > 0)
  const canRedo = computed(() => currentHistoryIndex.value < viewHistory.value.length - 1)

  // ========== AUTO HISTORY MANAGEMENT ==========

  /**
   * Автоматическое отслеживание изменений в видимых узлах и рёбрах
   */
  watch([() => nodesDataSet.value?.length, () => edgesDataSet.value?.length],
    ([newNodesCount, newEdgesCount], [oldNodesCount, oldEdgesCount]) => {
      // Не сохраняем при восстановлении из истории
      if (isRestoringFromHistory.value) {
        return
      }

      // Проверяем изменения в видимых элементах
      if (newNodesCount !== oldNodesCount || newEdgesCount !== oldEdgesCount) {
        console.log(`Изменение видимых элементов: узлы ${oldNodesCount} → ${newNodesCount}, рёбра ${oldEdgesCount} → ${newEdgesCount}`)
        saveCurrentState()
      }
    },
    { flush: 'post' }
  )

  // ========== ACTIONS ==========

  /**
   * Установка ссылок на vis-network объекты
   */
  const setNetwork = (net, nodesDS, edgesDS) => {
    network.value = net
    nodesDataSet.value = nodesDS
    edgesDataSet.value = edgesDS
  }

  /**
   * Установка ошибки
   */
  const setError = (msg) => {
    error.value = msg
    if (errorTimeout) {
      clearTimeout(errorTimeout)
    }
    errorTimeout = setTimeout(() => {
      clearError()
    }, 5000)
  }

  /**
   * Очистка ошибки
   */
  const clearError = () => {
    if (errorTimeout) {
      clearTimeout(errorTimeout)
      errorTimeout = null
    }
    error.value = null
  }

  /**
   * Валидация ответа от API
   */
  const validateApiResponse = (data, requiredFields = []) => {
    if (!data || typeof data !== 'object') {
      throw new Error('Неверный формат ответа от сервера')
    }

    for (const field of requiredFields) {
      if (!(field in data)) {
        throw new Error(`Отсутствует обязательное поле: ${field}`)
      }
    }

    return true
  }

  /**
   * Загрузка списка доступных узлов
   */
  const loadNodes = async () => {
    try {
      isLoading.value = true
      clearError()

      const params = new URLSearchParams()
      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/nodes${params.toString() ? '?' + params.toString() : ''}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`)
      }

      const data = await response.json()

      if (!Array.isArray(data)) {
        throw new Error('Неверный формат данных: ожидается массив узлов')
      }

      nodes.value = data

      console.log(`Загружено узлов: ${nodes.value.length}`)

      if (startNode.value) {
        console.log('Автозагрузка графа для узла:', startNode.value)
        await loadGraph()
      }
    } catch (err) {
      console.error('Ошибка загрузки узлов:', err)
      setError(`Не удалось загрузить список узлов: ${err.message}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Загрузка и отображение графа
   */
  const loadGraph = async () => {
    if (!nodesDataSet.value || !edgesDataSet.value) {
      error.value = 'Граф не инициализирован'
      return
    }

    try {
      isLoading.value = true
      error.value = null

      const params = new URLSearchParams()

      if (startNode.value) {
        params.append('start', startNode.value)
        params.append('depth', depth.value)
      }

      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/graph?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // Очистка текущего графа
      nodesDataSet.value.clear()
      edgesDataSet.value.clear()

      // Применение оформления
      const visualNodes = applyNodesVisualization(data.nodes || [], theme.value)
      const visualEdges = applyEdgesVisualization(data.edges || [], theme.value)

      // Добавление новых данных в визуализацию
      if (visualNodes.length > 0) {
        nodesDataSet.value.add(visualNodes)
      }

      if (visualEdges.length > 0) {
        edgesDataSet.value.add(visualEdges)
      }

      // Применить тему после загрузки
      applyTheme()

    } catch (err) {
      console.error('Ошибка загрузки графа:', err)
      setError(`Не удалось загрузить граф: ${err.message}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Применение темы к графу
   */
  const applyTheme = () => {
    if (network.value) {
      network.value.setOptions({
        nodes: {
          color: {
            background: theme.value === 'dark' ? '#333' : '#eee',
            border: theme.value === 'dark' ? '#666' : '#ccc',
          },
          font: {
            color: theme.value === 'dark' ? '#eee' : '#333',
          },
        },
        edges: {
          color: {
            color: theme.value === 'dark' ? '#848484' : '#999',
            highlight: theme.value === 'dark' ? '#848484' : '#999',
            hover: theme.value === 'dark' ? '#848484' : '#999',
          },
        },
      })
    }
  }

  /**
   * Обновление выбранных узлов
   */
  const updateSelectedNodes = async (nodeIds) => {
    try {
      selectedNodesList.value = []

      for (const nodeId of nodeIds) {
        try {
          const url = `${API_BASE}/object_details?id=${encodeURIComponent(nodeId)}`
          const response = await fetch(url)

          if (response.ok) {
            const data = await response.json()
            selectedNodesList.value.push(data)
          } else {
            console.warn(`Failed to load details for node ${nodeId}`)
            selectedNodesList.value.push({ _id: nodeId, projects: [] })
          }
        } catch (err) {
          console.error(`Error loading node ${nodeId}:`, err)
          selectedNodesList.value.push({ _id: nodeId, projects: [] })
        }
      }
    } catch (err) {
      console.error('Error updating selected nodes:', err)
    }
  }

  /**
   * Обновление выборки рёбер
   */
  const updateSelectedEdges = async (edgeIds) => {
    try {
      selectedEdgesList.value = []

      for (const edgeId of edgeIds) {
        try {
          const url = `${API_BASE}/object_details?id=${encodeURIComponent(edgeId)}`
          const response = await fetch(url)

          if (response.ok) {
            const data = await response.json()
            selectedEdgesList.value.push(data)
          } else {
            console.warn(`Failed to load details for edge ${edgeId}`)
            selectedEdgesList.value.push({ _id: edgeId, projects: [] })
          }
        } catch (err) {
          console.error(`Error loading edge ${edgeId}:`, err)
          selectedEdgesList.value.push({ _id: edgeId, projects: [] })
        }
      }
    } catch (err) {
      console.error('Error updating selected edges:', err)
    }
  }

  /**
   * Очистка выборки
   */
  const clearSelection = () => {
    selectedNodesList.value = []
    selectedEdgesList.value = []
  }

  // ========== HISTORY MANAGEMENT ==========

  /**
   * Сохранение текущего состояния в историю
   */
  const saveCurrentState = () => {
    const now = Date.now()

    // Дополнительная проверка: не сохраняем при восстановлении из истории
    if (isRestoringFromHistory.value) {
      console.log('Пропущено сохранение: восстановление из истории')
      return
    }

    const currentState = {
      startNode: startNode.value,
      depth: depth.value,
      project: project.value,
      nodeCount: nodeCount.value,
      edgeCount: edgeCount.value,
      nodes: getCurrentNodesData(), // Полные данные узлов
      edges: getCurrentEdgesData(), // Полные данные рёбер
      timestamp: now
    }

    // Удалить все состояния после текущего индекса (если есть)
    if (currentHistoryIndex.value < viewHistory.value.length - 1) {
      viewHistory.value = viewHistory.value.slice(0, currentHistoryIndex.value + 1)
    }

    // Добавить новое состояние
    viewHistory.value.push(currentState)
    currentHistoryIndex.value = viewHistory.value.length - 1

    // Ограничить размер истории
    if (viewHistory.value.length > maxHistorySize) {
      viewHistory.value.shift()
      currentHistoryIndex.value--
    }

    const displayName = currentState.startNode || 'всё'
    console.log(`Сохранено состояние: ${displayName} (${currentState.nodeCount} узлов, ${currentState.edgeCount} рёбер)`)
    console.log(`История: ${viewHistory.value.length} состояний, текущий индекс: ${currentHistoryIndex.value}`)
  }

  /**
   * Получить текущие данные узлов
   */
  const getCurrentNodesData = () => {
    if (!nodesDataSet.value) return []
    return nodesDataSet.value.get()
  }

  /**
   * Получить текущие данные рёбер
   */
  const getCurrentEdgesData = () => {
    if (!edgesDataSet.value) return []
    return edgesDataSet.value.get()
  }

  /**
   * Восстановление состояния из истории
   */
  const restoreState = (state) => {
    console.log(`Восстановление состояния: ${state.startNode || 'всё'} (${state.nodeCount} узлов)`)
    isRestoringFromHistory.value = true
    
    startNode.value = state.startNode
    depth.value = state.depth
    project.value = state.project

    // Восстановить состояние визуализации напрямую
    restoreVisualizationState(state)

    // Выключить флаг после завершения восстановления
    setTimeout(() => {
      isRestoringFromHistory.value = false
      console.log('Восстановление завершено, флаг сброшен')
    }, 500)
  }

  /**
   * Восстановление состояния визуализации напрямую
   */
  const restoreVisualizationState = (state) => {
    console.log('Восстановление визуализации напрямую')

    // Очистить текущую визуализацию
    if (nodesDataSet.value) {
      nodesDataSet.value.clear()
    }
    if (edgesDataSet.value) {
      edgesDataSet.value.clear()
    }

    // Применить оформление к восстановленным данным
    const visualNodes = applyNodesVisualization(state.nodes || [], theme.value)
    const visualEdges = applyEdgesVisualization(state.edges || [], theme.value)

    // Добавить узлы в визуализацию
    if (visualNodes.length > 0) {
      nodesDataSet.value.add(visualNodes)
    }

    // Добавить рёбра в визуализацию
    if (visualEdges.length > 0) {
      edgesDataSet.value.add(visualEdges)
    }

    console.log(`Восстановлено: ${visualNodes.length} узлов, ${visualEdges.length} рёбер`)
  }

  /**
   * Показать весь граф
   */
  const showAllGraph = () => {
    startNode.value = ''
    loadGraph()
  }

  /**
   * Отменить последнее изменение отображения
   */
  const undoView = () => {
    if (canUndo.value) {
      console.log(`Отмена: текущий индекс ${currentHistoryIndex.value}, история ${viewHistory.value.length} состояний`)
      currentHistoryIndex.value--
      const state = viewHistory.value[currentHistoryIndex.value]
      restoreState(state)
      const displayName = state.startNode || 'всё'
      console.log(`Отменено: ${displayName} (${state.nodeCount} узлов)`)
    }
  }

  /**
   * Вернуть отменённое изменение отображения
   */
  const redoView = () => {
    if (canRedo.value) {
      currentHistoryIndex.value++
      const state = viewHistory.value[currentHistoryIndex.value]
      restoreState(state)
      const displayName = state.startNode || 'всё'
      console.log(`Возвращено: ${displayName} (${state.nodeCount} узлов)`)
    }
  }

  // ========== RETURN ==========

  const api = {
    // State
    nodes,
    startNode,
    depth,
    project,
    theme,
    network,
    nodesDataSet,
    edgesDataSet,
    isLoading,
    error,
    selectedNodesList,
    selectedEdgesList,
    viewHistory,
    currentHistoryIndex,

    // Computed
    nodeCount,
    edgeCount,
    selectionCount,
    selectedNodesCount,
    selectedEdgesCount,
    canUndo,
    canRedo,

    // Actions
    setNetwork,
    loadNodes,
    loadGraph,
    applyTheme,
    updateSelectedNodes,
    updateSelectedEdges,
    clearSelection,

    // History management
    showAllGraph,
    undoView,
    redoView,
  }

  return api
})
