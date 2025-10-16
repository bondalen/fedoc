import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import io from 'socket.io-client'

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
  const documentCache = ref(new Map())  // Кэш загруженных документов
  
  // Выборка для отправки в Cursor AI
  const selectedNodesList = ref([])  // Массив выбранных узлов с деталями
  const selectedEdgesList = ref([])  // Массив выбранных рёбер с деталями
  
  // WebSocket соединение
  let socket = null
  const isSocketConnected = ref(false)
  
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
   * Установка ошибки с автоочисткой через 5 секунд
   */
  const setError = (message) => {
    error.value = message
    
    // Очистить предыдущий таймер
    if (errorTimeout) {
      clearTimeout(errorTimeout)
    }
    
    // Установить новый таймер
    errorTimeout = setTimeout(() => {
      error.value = null
    }, 5000)
  }
  
  /**
   * Очистка ошибки вручную
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
      
      // API возвращает массив напрямую
      if (!Array.isArray(data)) {
        throw new Error('Неверный формат данных: ожидается массив узлов')
      }
      
      nodes.value = data
      
      // Установить первый узел по умолчанию, если не выбран
      if (nodes.value.length > 0 && !startNode.value) {
        startNode.value = nodes.value[0]._id
      }
      
      console.log(`Загружено узлов: ${nodes.value.length}`)
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
    if (!startNode.value) {
      error.value = 'Не выбран стартовый узел'
      return
    }
    
    if (!nodesDataSet.value || !edgesDataSet.value) {
      error.value = 'Граф не инициализирован'
      return
    }
    
    try {
      isLoading.value = true
      error.value = null
      
      const params = new URLSearchParams({
        start: startNode.value,
        depth: depth.value
      })
      
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
      
      // Добавление новых данных
      if (data.nodes && data.nodes.length > 0) {
        nodesDataSet.value.add(data.nodes)
      }
      
      if (data.edges && data.edges.length > 0) {
        edgesDataSet.value.add(data.edges)
      }
      
      // Оптимизация для больших графов
      const nodeCount = data.nodes ? data.nodes.length : 0
      if (nodeCount > 100) {
        console.log(`Большой граф (${nodeCount} узлов), применяем оптимизации`)
        // Уменьшить количество итераций стабилизации для больших графов
        if (network.value) {
          network.value.setOptions({
            physics: {
              stabilization: {
                iterations: Math.max(200, 800 - nodeCount)
              }
            }
          })
        }
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
   * Обработка выбора узла на графе
   */
  const selectNode = async (nodeId) => {
    try {
      await loadObjectDetails(nodeId)
      showDetails.value = true
    } catch (err) {
      console.error('Ошибка загрузки деталей узла:', err)
      setError(`Не удалось загрузить детали узла: ${err.message}`)
    }
  }
  
  /**
   * Обработка выбора ребра на графе
   */
  const selectEdge = async (edgeId) => {
    try {
      await loadObjectDetails(edgeId)
      showDetails.value = true
    } catch (err) {
      console.error('Ошибка загрузки деталей ребра:', err)
      setError(`Не удалось загрузить детали ребра: ${err.message}`)
    }
  }
  
  /**
   * Загрузка деталей объекта (узла или ребра)
   */
  const loadObjectDetails = async (objectId) => {
    try {
      const url = `${API_BASE}/object_details?id=${encodeURIComponent(objectId)}`
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      // API возвращает объект напрямую
      selectedObject.value = data
      
    } catch (err) {
      console.error('Ошибка загрузки деталей объекта:', err)
      throw err
    }
  }
  
  /**
   * Загрузка деталей документа (для раскрытия ссылок)
   */
  const loadDocumentDetails = async (docId) => {
    // Проверить кэш
    if (documentCache.value.has(docId)) {
      console.log(`Документ загружен из кэша: ${docId}`)
      return documentCache.value.get(docId)
    }
    
    try {
      const url = `${API_BASE}/object_details?id=${encodeURIComponent(docId)}`
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`)
      }
      
      const data = await response.json()
      
      // API возвращает объект напрямую
      // Сохранить в кэш
      documentCache.value.set(docId, data)
      loadedDocs.value.add(docId)
      
      console.log(`Документ загружен с сервера: ${docId}`)
      return data
      
    } catch (err) {
      console.error('Ошибка загрузки документа:', err)
      throw err
    }
  }
  
  /**
   * Закрытие панели деталей
   */
  const closeDetails = () => {
    showDetails.value = false
    selectedObject.value = null
  }
  
  /**
   * Открытие панели полного текста
   */
  const openFullText = (text) => {
    fullText.value = text
    showFullText.value = true
  }
  
  /**
   * Закрытие панели полного текста
   */
  const closeFullText = () => {
    showFullText.value = false
    fullText.value = ''
  }
  
  /**
   * Переключение видимости панели полного текста
   */
  const toggleFullText = () => {
    if (showFullText.value) {
      closeFullText()
    } else if (fullText.value) {
      showFullText.value = true
    }
  }
  
  /**
   * Фокусировка на узле в графе
   */
  const focusNode = (nodeId) => {
    if (!network.value || !nodesDataSet.value) return
    
    try {
      // Проверить, существует ли узел в графе
      const node = nodesDataSet.value.get(nodeId)
      if (!node) {
        console.warn(`Узел ${nodeId} не найден в графе`)
        setError(`Узел ${nodeId} не отображается на текущем графе`)
        return
      }
      
      console.log(`Попытка фокусировки на узле: ${nodeId}`)
      
      // Сначала фокус
      network.value.focus(nodeId, {
        scale: 1.2,
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad'
        }
      })
      
      // Выделить узел после фокусировки (обернуто в try-catch)
      setTimeout(() => {
        try {
          if (network.value) {
            // Используем более безопасный метод выделения
            const selectionHandler = network.value.selectionHandler
            if (selectionHandler && selectionHandler.selectNodes) {
              selectionHandler.selectNodes([nodeId], false)
            }
          }
        } catch (selectionError) {
          // Игнорируем ошибки выделения - фокусировка уже сработала
          console.debug('Ошибка выделения узла (не критично):', selectionError)
        }
      }, 100)
      
      console.log(`Фокусировка на узле успешна: ${nodeId}`)
    } catch (err) {
      console.error('Ошибка фокусировки на узле:', err)
      setError(`Не удалось сфокусироваться на узле: ${err.message}`)
    }
  }
  
  /**
   * Подгонка графа под размер экрана
   */
  const fitGraph = () => {
    if (!network.value) return
    
    try {
      network.value.fit({
        animation: {
          duration: 500,
          easingFunction: 'easeInOutQuad'
        }
      })
    } catch (err) {
      console.error('Ошибка подгонки графа:', err)
    }
  }
  
  /**
   * Применение темы к графу
   */
  const applyTheme = () => {
    if (!network.value) return
    
    const isDark = theme.value === 'dark'
    
    // Цвета для темы
    const labelColor = isDark ? '#E0E0E0' : '#212121'
    const edgeColor = isDark ? '#B0BEC5' : '#424242'
    const strokeColor = isDark ? '#000' : '#fff'
    
    // Обновление настроек сети
    network.value.setOptions({
      nodes: {
        font: { 
          color: labelColor,
          bold: {
            color: isDark ? '#ffffff' : '#000000'
          }
        },
        color: {
          background: isDark ? '#2d3748' : '#ffffff',
          border: isDark ? '#4a5568' : '#cbd5e0',
          highlight: {
            background: isDark ? '#4299e1' : '#3182ce',
            border: isDark ? '#63b3ed' : '#2c5282'
          },
          hover: {
            background: isDark ? '#3a4a5e' : '#e8f4fd',
            border: isDark ? '#5a6a88' : '#90caf9'
          }
        },
        shadow: {
          enabled: isDark,
          color: 'rgba(0,0,0,0.3)',
          size: 5,
          x: 2,
          y: 2
        }
      },
      edges: {
        font: { 
          color: labelColor,
          strokeColor: strokeColor,
          strokeWidth: 2
        },
        color: { 
          color: edgeColor,
          highlight: isDark ? '#4299e1' : '#1976D2',
          hover: isDark ? '#64B5F6' : '#42A5F5'
        }
      }
    })
    
    // Применить тему к body
    document.body.style.background = isDark ? '#111' : '#f5f5f5'
    document.body.style.color = isDark ? '#e0e0e0' : '#333'
  }
  
  /**
   * Изменение проекта (с перезагрузкой)
   */
  const changeProject = async () => {
    await loadNodes()
    await loadGraph()
  }
  
  /**
   * Инициализация WebSocket соединения
   */
  const initWebSocket = () => {
    try {
      // Подключение к WebSocket серверу
      socket = io('http://localhost:8899', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5
      })
      
      // Обработка успешного подключения
      socket.on('connect', () => {
        console.log('✓ WebSocket connected')
        isSocketConnected.value = true
      })
      
      // Обработка отключения
      socket.on('disconnect', () => {
        console.log('✗ WebSocket disconnected')
        isSocketConnected.value = false
      })
      
      // Обработка подтверждения соединения от сервера
      socket.on('connection_established', (data) => {
        console.log('✓ Connection established:', data)
      })
      
      // Обработка запроса выборки от сервера (MCP команда)
      socket.on('request_selection', () => {
        console.log('→ Server requested selection, sending...')
        sendSelectionToServer()
      })
      
      // Обработка ошибок
      socket.on('error', (error) => {
        console.error('WebSocket error:', error)
      })
      
      console.log('WebSocket initialization started')
    } catch (err) {
      console.error('Failed to initialize WebSocket:', err)
      setError('Не удалось подключиться к WebSocket серверу')
    }
  }
  
  /**
   * Закрытие WebSocket соединения
   */
  const closeWebSocket = () => {
    if (socket) {
      socket.disconnect()
      socket = null
      isSocketConnected.value = false
      console.log('WebSocket connection closed')
    }
  }
  
  /**
   * Отправка текущей выборки на сервер через WebSocket
   */
  const sendSelectionToServer = () => {
    if (!socket || !isSocketConnected.value) {
      console.warn('WebSocket not connected, cannot send selection')
      return
    }
    
    // Получить детали выбранных объектов
    const selectionData = {
      nodes: selectedNodesList.value,
      edges: selectedEdgesList.value,
      timestamp: Date.now()
    }
    
    console.log(`Sending selection: ${selectedNodesList.value.length} nodes, ${selectedEdgesList.value.length} edges`)
    socket.emit('selection_response', selectionData)
  }
  
  /**
   * Обновление выборки узлов
   */
  const updateSelectedNodes = async (nodeIds) => {
    try {
      // Очистить текущую выборку узлов
      selectedNodesList.value = []
      
      // Загрузить детали для каждого выбранного узла
      for (const nodeId of nodeIds) {
        try {
          const url = `${API_BASE}/object_details?id=${encodeURIComponent(nodeId)}`
          const response = await fetch(url)
          
          if (response.ok) {
            const data = await response.json()
            selectedNodesList.value.push(data)
          } else {
            console.warn(`Failed to load details for node ${nodeId}`)
            // Добавляем хотя бы ID
            selectedNodesList.value.push({ _id: nodeId, name: 'Не удалось загрузить' })
          }
        } catch (err) {
          console.error(`Error loading node ${nodeId}:`, err)
          selectedNodesList.value.push({ _id: nodeId, name: 'Ошибка загрузки' })
        }
      }
      
      console.log(`Updated node selection: ${selectedNodesList.value.length} nodes`)
    } catch (err) {
      console.error('Error updating selected nodes:', err)
    }
  }
  
  /**
   * Обновление выборки рёбер
   */
  const updateSelectedEdges = async (edgeIds) => {
    try {
      // Очистить текущую выборку рёбер
      selectedEdgesList.value = []
      
      // Загрузить детали для каждого выбранного ребра
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
      
      console.log(`Updated edge selection: ${selectedEdgesList.value.length} edges`)
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
    console.log('Selection cleared')
  }
  
  // ========== RETURN ==========
  
  return {
    // State
    nodes,
    startNode,
    depth,
    project,
    theme,
    network,
    nodesDataSet,
    edgesDataSet,
    selectedObject,
    showDetails,
    fullText,
    showFullText,
    loadedDocs,
    isLoading,
    error,
    
    // Selection state
    selectedNodesList,
    selectedEdgesList,
    isSocketConnected,
    
    // Computed
    nodeCount,
    edgeCount,
    selectionCount,
    selectedNodesCount,
    selectedEdgesCount,
    
    // Actions
    setNetwork,
    loadNodes,
    loadGraph,
    selectNode,
    selectEdge,
    loadObjectDetails,
    loadDocumentDetails,
    closeDetails,
    openFullText,
    closeFullText,
    toggleFullText,
    focusNode,
    fitGraph,
    applyTheme,
    changeProject,
    clearError,
    
    // WebSocket actions
    initWebSocket,
    closeWebSocket,
    sendSelectionToServer,
    
    // Selection actions
    updateSelectedNodes,
    updateSelectedEdges,
    clearSelection
  }
})

