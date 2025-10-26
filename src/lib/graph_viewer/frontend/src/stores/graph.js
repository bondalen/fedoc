import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
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

      // Добавление новых данных в визуализацию
      if (data.nodes && data.nodes.length > 0) {
        nodesDataSet.value.add(data.nodes)
      }

      if (data.edges && data.edges.length > 0) {
        edgesDataSet.value.add(data.edges)
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
    if (!network.value) return

    const isDark = theme.value === 'dark'
    
    // Основные цвета
    const labelColor = isDark ? '#e0e0e0' : '#333'
    const edgeColor = isDark ? '#B0BEC5' : '#37474F'
    const strokeColor = isDark ? '#000' : '#fff'
    const strokeWidth = isDark ? 2 : 4
    
    // Цвета для интерактивных состояний (универсальные для обеих тем)
    const highlightColor = '#D2691E'                          // 🔥 оранжевый для выделения
    const hoverColor = '#9c27b0'                              // 💜 фиолетовый для hover
    
    // Обновление настроек сети
    network.value.setOptions({
      nodes: {
        font: { 
          color: labelColor,
          size: 12,
          bold: {
            color: isDark ? '#ffffff' : '#000000'
          }
        },
        color: {
          background: isDark ? '#2d3748' : '#ffffff',        // белый для light
          border: isDark ? '#4a5568' : '#e0e0e0',            // светлее для light
          highlight: {
            background: isDark ? '#2d3748' : '#f8f9fa',      // фон не меняется
            border: highlightColor                            // 🔥 оранжевый
          },
          hover: {
            background: isDark ? '#2d3748' : '#f8f9fa',      // фон не меняется
            border: hoverColor                                // 💜 фиолетовый
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
        width: isDark ? 2 : 2.5,                             // толще для light
        font: { 
          color: labelColor,
          strokeColor: strokeColor,
          strokeWidth: strokeWidth,                          // используем переменную
          size: 12
          // bold удален - vis-network не принимает boolean для этого параметра
        },
        color: { 
          color: edgeColor,
          highlight: highlightColor,                         // 🔥 оранжевый
          hover: hoverColor                                  // 💜 фиолетовый
        }
      }
    })
    
    // 🎯 ПРИНУДИТЕЛЬНОЕ ИЗМЕНЕНИЕ ФОНА через CSS и DOM
    const canvas = document.querySelector('#graph canvas')
    if (canvas) {
      canvas.style.backgroundColor = isDark ? '#1e1e1e' : '#ffffff'
    }
    
    // Принудительно обновить все узлы с новыми цветами
    if (nodesDataSet.value && nodesDataSet.value.length > 0) {
      const allNodes = nodesDataSet.value.get()
      const updatedNodes = allNodes.map(node => ({
        ...node,
        color: {
          background: isDark ? '#2d3748' : '#ffffff',        // белый для light
          border: isDark ? '#4a5568' : '#e0e0e0',             // светлее для light
          highlight: {
            background: isDark ? '#2d3748' : '#ffffff',
            border: highlightColor
          },
          hover: {
            background: isDark ? '#2d3748' : '#ffffff',
            border: hoverColor
          }
        }
      }))
      nodesDataSet.value.update(updatedNodes)
    }
    
    // Принудительно обновить все рёбра с новыми цветами
    if (edgesDataSet.value && edgesDataSet.value.length > 0) {
      const allEdges = edgesDataSet.value.get()
      const updatedEdges = allEdges.map(edge => ({
        ...edge,
        color: {
          color: edgeColor,
          highlight: highlightColor,
          hover: hoverColor
        }
      }))
      edgesDataSet.value.update(updatedEdges)
    }
    
    // Принудительно перерисовать сеть
    if (network.value) {
      network.value.redraw()
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

  /**
   * Подогнать граф к экрану
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
      console.error('Error fitting graph:', err)
    }
  }
  
  /**
   * Смена проекта
   */
  const changeProject = async () => {
    await loadNodes()
    await loadGraph()
  }

  /**
   * Загрузка деталей документа
   */
  const loadDocumentDetails = async (docId) => {
    // Проверить кэш
    if (documentCache.value.has(docId)) {
      console.log(`Документ загружен из кэша: ${docId}`)
      return documentCache.value.get(docId)
    }
    
    try {
      // Поддержка документных коллекций в PostgreSQL
      // Ожидаемые форматы: 'projects/<key>' или 'rules/<key>'
      let url
      if (typeof docId === 'string' && docId.includes('/')) {
        const [collection, key] = docId.split('/', 2)
        if ((collection === 'projects' || collection === 'rules') && key) {
          url = `${API_BASE}/object_details?collection=${encodeURIComponent(collection)}&key=${encodeURIComponent(key)}`
        } else {
          throw new Error(`Неверный формат ID документа: ${docId}`)
        }
      } else {
        // Fallback для простых ID
        url = `${API_BASE}/object_details?id=${encodeURIComponent(docId)}`
      }
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Кэшировать результат
      documentCache.value.set(docId, data)
      loadedDocs.value.add(docId)
      
      console.log(`Документ загружен: ${docId}`)
      return data
    } catch (err) {
      console.error(`Ошибка загрузки документа ${docId}:`, err)
      throw err
    }
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
   * Загрузка деталей объекта
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
   * Закрытие панели деталей
   */
  const closeDetails = () => {
    showDetails.value = false
    selectedObject.value = null
  }

  // ========== EXPAND/HIDE OPERATIONS ==========

  /**
   * Расширить узел - показать потомков (1 уровень вниз)
   */
  const expandNodeChildren = async (nodeId) => {
    try {
      isLoading.value = true

      const params = new URLSearchParams({
        node_id: nodeId,
        direction: 'outbound',
        theme: theme.value
      })

      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/expand_node?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      // Добавить новые узлы и рёбра
      const newNodes = data.nodes || []
      const newEdges = data.edges || []

      let addedNodesCount = 0
      let addedEdgesCount = 0

      // Добавить узлы, которых еще нет
      for (const node of newNodes) {
        const existsInDataSet = nodesDataSet.value.get(node.id)
        if (!existsInDataSet) {
          nodesDataSet.value.add(node)
          addedNodesCount++
        }
      }

      // Добавить рёбра, которых еще нет
      for (const edge of newEdges) {
        const existsInDataSet = edgesDataSet.value.get(edge.id)
        if (!existsInDataSet) {
          edgesDataSet.value.add(edge)
          addedEdgesCount++
        }
      }

      console.log(`Expanded ${nodeId} (children): +${addedNodesCount} nodes, +${addedEdgesCount} edges`)

      if (addedNodesCount === 0 && addedEdgesCount === 0) {
        setError('Нет нижестоящих вершин для отображения')
      }

    } catch (err) {
      console.error('Error expanding node children:', err)
      setError(`Не удалось отобразить нижестоящие вершины: ${err.message}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Расширить узел - показать предков (1 уровень вверх)
   */
  const expandNodeParents = async (nodeId) => {
    try {
      isLoading.value = true

      const params = new URLSearchParams({
        node_id: nodeId,
        direction: 'inbound',
        theme: theme.value
      })

      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/expand_node?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      const newNodes = data.nodes || []
      const newEdges = data.edges || []

      let addedNodesCount = 0
      let addedEdgesCount = 0

      for (const node of newNodes) {
        const existsInDataSet = nodesDataSet.value.get(node.id)
        if (!existsInDataSet) {
          nodesDataSet.value.add(node)
          addedNodesCount++
        }
      }

      for (const edge of newEdges) {
        const existsInDataSet = edgesDataSet.value.get(edge.id)
        if (!existsInDataSet) {
          edgesDataSet.value.add(edge)
          addedEdgesCount++
        }
      }

      console.log(`Expanded ${nodeId} (parents): +${addedNodesCount} nodes, +${addedEdgesCount} edges`)

      if (addedNodesCount === 0 && addedEdgesCount === 0) {
        setError('Нет вышестоящих вершин для отображения')
      }

    } catch (err) {
      console.error('Error expanding node parents:', err)
      setError(`Не удалось отобразить вышестоящие вершины: ${err.message}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Скрыть узел с потомками (рекурсия)
   */
  const hideNodeWithChildren = async (nodeId) => {
    try {
      isLoading.value = true

      const params = new URLSearchParams({
        node_id: nodeId,
        direction: 'outbound',
        max_depth: 100
      })

      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/subgraph?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      // Рекурсивная клиентская логика для поиска всех связанных узлов
      const nodeIds = [nodeId]
      const edgeIds = []
      const processedNodes = new Set([nodeId])

      // Рекурсивная функция для поиска всех дочерних узлов
      const findChildrenRecursively = (currentNodeId) => {
        if (edgesDataSet.value) {
          for (const edge of edgesDataSet.value.get()) {
            // Проверяем, является ли узел началом ребра (исходящие связи)
            const edgeStartId = edge.from || edge.start_id
            if (edgeStartId == currentNodeId) {
              const childNodeId = edge.to || edge.end_id
              if (childNodeId && !processedNodes.has(childNodeId)) {
                nodeIds.push(childNodeId)
                processedNodes.add(childNodeId)
                // Рекурсивно ищем детей этого узла
                findChildrenRecursively(childNodeId)
              }
              if (edge.id || edge._id) {
                edgeIds.push(edge.id || edge._id)
              }
            }
          }
        }
      }

      // Запускаем рекурсивный поиск
      findChildrenRecursively(nodeId)

      // Удалить из визуализации - преобразуем в числа
      const numericNodeIds = nodeIds.map(id => parseInt(id))
      const numericEdgeIds = edgeIds.map(id => parseInt(id))

      nodesDataSet.value.remove(numericNodeIds)
      edgesDataSet.value.remove(numericEdgeIds)

      // Принудительно обновить визуализацию
      if (network.value) {
        network.value.redraw()
      }

      console.log(`Hidden ${nodeId} with children: ${nodeIds.length} nodes, ${edgeIds.length} edges`)

    } catch (err) {
      console.error('Error hiding node with children:', err)
      setError(`Не удалось скрыть узел с нижестоящими: ${err.message}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Скрыть узел с предками (рекурсия)
   */
  const hideNodeWithParents = async (nodeId) => {
    try {
      isLoading.value = true

      const params = new URLSearchParams({
        node_id: nodeId,
        direction: 'inbound',
        max_depth: 100
      })

      if (project.value) {
        params.append('project', project.value)
      }

      const url = `${API_BASE}/subgraph?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      const nodeIds = [nodeId]
      const edgeIds = []
      const processedNodes = new Set([nodeId])

      const findParentsRecursively = (currentNodeId) => {
        if (edgesDataSet.value) {
          for (const edge of edgesDataSet.value.get()) {
            const edgeEndId = edge.to || edge.end_id
            if (edgeEndId == currentNodeId) {
              const parentNodeId = edge.from || edge.start_id
              if (parentNodeId && !processedNodes.has(parentNodeId)) {
                nodeIds.push(parentNodeId)
                processedNodes.add(parentNodeId)
                findParentsRecursively(parentNodeId)
              }
              if (edge.id || edge._id) {
                edgeIds.push(edge.id || edge._id)
              }
            }
          }
        }
      }

      findParentsRecursively(nodeId)

      // Удалить из визуализации - преобразуем в числа
      const numericNodeIds = nodeIds.map(id => parseInt(id))
      const numericEdgeIds = edgeIds.map(id => parseInt(id))

      nodesDataSet.value.remove(numericNodeIds)
      edgesDataSet.value.remove(numericEdgeIds)

      // Принудительно обновить визуализацию
      if (network.value) {
        network.value.redraw()
      }

      console.log(`Hidden ${nodeId} with parents: ${nodeIds.length} nodes, ${edgeIds.length} edges`)

    } catch (err) {
      console.error('Error hiding node with parents:', err)
      setError(`Не удалось скрыть узел с вышестоящими: ${err.message}`)
    } finally {
      isLoading.value = false
    }
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

    // Добавить узлы в визуализацию
    if (state.nodes && state.nodes.length > 0) {
      nodesDataSet.value.add(state.nodes)
    }

    // Добавить рёбра в визуализацию
    if (state.edges && state.edges.length > 0) {
      edgesDataSet.value.add(state.edges)
    }

    console.log(`Восстановлено: ${state.nodes?.length || 0} узлов, ${state.edges?.length || 0} рёбер`)
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

  // ========== WEBSOCKET FUNCTIONALITY ==========
  
  /**
   * Инициализация WebSocket соединения
   */
  const initWebSocket = () => {
    try {
      // Подключение к WebSocket серверу через Vite proxy
      socket = io({
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

    // Получить выбранные узлы и рёбра из vis-network
    const selectedNodes = network.value ? network.value.getSelectedNodes() : []
    const selectedEdges = network.value ? network.value.getSelectedEdges() : []

    // Подготовить данные узлов
    const nodesPayload = selectedNodes.map((nid) => {
      let meta = {}
      try { meta = nodesDataSet.value ? (nodesDataSet.value.get(nid) || {}) : {} } catch {}
      return {
        id: meta.id || nid,
        key: meta._key || meta.key || null,
        label: meta.label || meta.name || null,
      }
    })

    // Подготовить данные рёбер
    const edgesPayload = selectedEdges.map((eid) => {
      let meta = {}
      try { meta = edgesDataSet.value ? (edgesDataSet.value.get(eid) || {}) : {} } catch {}
      return {
        id: meta.id || eid,
        from: meta.from || null,
        to: meta.to || null,
        label: meta.label || null,
      }
    })

    const selectionData = {
      nodes: nodesPayload,
      edges: edgesPayload,
      timestamp: Date.now()
    }

    console.log(`Sending selection: ${nodesPayload.length} nodes, ${edgesPayload.length} edges`)
    socket.emit('selection_response', selectionData)
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
    selectedObject,
    showDetails,
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
    fitGraph,
    changeProject,
    loadDocumentDetails,
    closeFullText,
    toggleFullText,
    loadObjectDetails,
    selectNode,
    selectEdge,
    closeDetails,

    // Expand/Hide actions
    expandNodeChildren,
    expandNodeParents,
    hideNodeWithChildren,
    hideNodeWithParents,
    
    // History management
    showAllGraph,
    undoView,
    redoView,
    
    // WebSocket actions
    initWebSocket,
    closeWebSocket,
    sendSelectionToServer,
  }

  return api
})
