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
  const documentCache = ref(new Map())  // Кэш загруженных документов
  
  // Выборка для отправки в Cursor AI
  const selectedNodesList = ref([])  // Массив выбранных узлов с деталями
  const selectedEdgesList = ref([])  // Массив выбранных рёбер с деталями
  
  // WebSocket соединение
  let socket = null
  const isSocketConnected = ref(false)
  
  // Управление видимостью узлов (для expand/collapse функционала)
  const allNodesData = ref([])      // Все загруженные узлы
  const allEdgesData = ref([])      // Все загруженные рёбра
  const hiddenNodes = ref(new Set()) // ID скрытых узлов
  const hiddenEdges = ref(new Set()) // ID скрытых рёбер
  
  // Статус загрузки
  const isLoading = ref(false)
  const error = ref(null)
  
  // Таймер для автоочистки ошибок
  let errorTimeout = null
  
  // История состояний отображения
  const viewHistory = ref([])           // Массив состояний
  const currentHistoryIndex = ref(-1)   // Текущий индекс в истории
  const maxHistorySize = 10            // Максимум состояний в истории
  const lastSavedState = ref(null)      // Последнее сохранённое состояние для предотвращения дублирования
  const isRestoringFromHistory = ref(false) // Флаг для предотвращения сохранения при восстановлении
  const lastSaveTime = ref(0) // Время последнего сохранения для предотвращения частых сохранений
  
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
  
  const visibleNodesCount = computed(() => {
    return allNodesData.value.length - hiddenNodes.value.size
  })
  
  const visibleEdgesCount = computed(() => {
    return allEdgesData.value.length - hiddenEdges.value.size
  })
  
  // Computed свойства для кнопок отмены/возврата
  const canUndo = computed(() => currentHistoryIndex.value > 0)
  const canRedo = computed(() => currentHistoryIndex.value < viewHistory.value.length - 1)
  
  // ========== AUTO HISTORY MANAGEMENT ==========
  
  /**
   * Debounced функция для сохранения состояния
   * Предотвращает частые сохранения при быстрых изменениях
   */
  let saveTimeout = null
  const debouncedSaveState = () => {
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }
    saveTimeout = setTimeout(() => {
      saveCurrentState()
    }, 200)
  }
  
  /**
   * Немедленное сохранение состояния
   * Используется для expand операций, чтобы каждая операция сохранялась отдельно
   */
  const immediateSaveState = () => {
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }
    // Немедленное сохранение без задержки
    saveCurrentState()
  }
  
  /**
   * Проверка значимости изменений в графе
   * Сохраняем только при реальных изменениях структуры
   */
  const isSignificantGraphChange = (newNodes, oldNodes, newEdges, oldEdges) => {
    // Изменение количества узлов или рёбер
    if (newNodes.length !== oldNodes.length || newEdges.length !== oldEdges.length) {
      console.log(`Изменение данных: узлы ${oldNodes.length} → ${newNodes.length}, рёбра ${oldEdges.length} → ${newEdges.length}`)
      return true
    }
    
    // Изменение количества скрытых узлов
    if (hiddenNodes.value.size !== (oldNodes.length - newNodes.length)) {
      console.log(`Изменение скрытых узлов: ${hiddenNodes.value.size} !== ${oldNodes.length - newNodes.length}`)
      return true
    }
    
    // Изменение количества скрытых рёбер
    if (hiddenEdges.value.size !== (oldEdges.length - newEdges.length)) {
      console.log(`Изменение скрытых рёбер: ${hiddenEdges.value.size} !== ${oldEdges.length - newEdges.length}`)
      return true
    }
    
    return false
  }
  
  /**
   * Автоматическое отслеживание изменений в видимых узлах и рёбрах
   * Отслеживает изменения в DataSet (визуализация) - основной watcher
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
        console.log('Автоматическое сохранение: изменения в видимых элементах')
        
        // Дополнительная проверка: не сохраняем если это восстановление из истории
        if (isRestoringFromHistory.value) {
          console.log('Пропущено сохранение: восстановление из истории')
          return
        }
        
        // Используем немедленное сохранение для expand операций
        // Это обеспечивает пошаговую отмену каждой операции
        immediateSaveState()
      }
    }, 
    { flush: 'post' }
  )
  
  /**
   * Отслеживание изменений в скрытых узлах и рёбрах
   * Отдельный watcher для более точного контроля
   */
  watch([hiddenNodes, hiddenEdges], 
    ([newHiddenNodes, newHiddenEdges], [oldHiddenNodes, oldHiddenEdges]) => {
      // Не сохраняем при восстановлении из истории
      if (isRestoringFromHistory.value) {
        return
      }
      
      if (newHiddenNodes.size !== oldHiddenNodes.size || 
          newHiddenEdges.size !== oldHiddenEdges.size) {
        console.log('Автоматическое сохранение: изменения в скрытых элементах')
        debouncedSaveState()
      }
    }, 
    { deep: true, flush: 'post' }
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
      const needsAutoLoad = nodes.value.length > 0 && !startNode.value
      if (needsAutoLoad) {
        // Передаём в API arango_key вместо AGE ID
        startNode.value = nodes.value[0]._key
      }
      
      console.log(`Загружено узлов: ${nodes.value.length}`)
      
      // Автоматически загрузить граф после установки стартового узла
      if (needsAutoLoad) {
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
  const loadGraph = async (saveState = true) => {
    if (!nodesDataSet.value || !edgesDataSet.value) {
      error.value = 'Граф не инициализирован'
      return
    }
    
    try {
      isLoading.value = true
      error.value = null
      
      const params = new URLSearchParams()
      
      // Добавить параметры только если они заданы
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
      
      // Сохранить все данные для управления видимостью
      allNodesData.value = data.nodes || []
      allEdgesData.value = data.edges || []
      
      // Сбросить скрытые узлы при новой загрузке
      hiddenNodes.value.clear()
      hiddenEdges.value.clear()
      
      // Добавление новых данных в визуализацию
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
      
      // Состояние автоматически сохраняется watchers
      
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
      // Поддержка документных коллекций в PostgreSQL
      // Ожидаемые форматы: 'projects/<key>' или 'rules/<key>'
      let url
      if (typeof docId === 'string' && docId.includes('/')) {
        const [collection, key] = docId.split('/', 2)
        if ((collection === 'projects' || collection === 'rules') && key) {
          url = `${API_BASE}/object_details?collection=${encodeURIComponent(collection)}&key=${encodeURIComponent(key)}`
        }
      }
      // Fallback: старый режим через id=
      if (!url) {
        url = `${API_BASE}/object_details?id=${encodeURIComponent(docId)}`
      }
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`)
      }
      const data = await response.json()
      
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
    
    // Цвета для темы (улучшенные для светлой темы)
    const labelColor = isDark ? '#E0E0E0' : '#000000'        // темнее для light
    const edgeColor = isDark ? '#B0BEC5' : '#37474F'         // темнее для light
    const strokeColor = isDark ? '#000' : '#fff'
    const strokeWidth = isDark ? 2 : 4                        // толще для light
    
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
    setTimeout(() => {
      // Ищем все canvas элементы в контейнере графа
      const graphContainer = document.getElementById('graph')
      if (graphContainer) {
        const canvases = graphContainer.querySelectorAll('canvas')
        canvases.forEach(canvas => {
          canvas.style.background = isDark ? '#1e1e1e' : '#ffffff'
        })
        
        // Также устанавливаем CSS переменную
        graphContainer.style.setProperty('--canvas-bg', isDark ? '#1e1e1e' : '#ffffff')
        graphContainer.style.background = isDark ? '#1e1e1e' : '#ffffff'
      }
    }, 100) // Небольшая задержка для инициализации
    
    // 🎯 РАДИКАЛЬНОЕ ОБНОВЛЕНИЕ - полная перезагрузка данных
    setTimeout(() => {
      if (network.value && nodesDataSet.value) {
        // Получаем все узлы
        const allNodes = nodesDataSet.value.get()
        
        // Обновляем каждый узел с новыми цветами
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
        
        // Полностью заменяем данные
        nodesDataSet.value.clear()
        nodesDataSet.value.add(updatedNodes)
        
        // Перерисовываем сеть
        network.value.redraw()
        network.value.fit()
      }
    }, 200) // Большая задержка для полного применения
    
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

    // Берём текущую выборку из store (без прямых вызовов vis-network)
    const nodeIds = (selectedNodesList.value || []).map(n => (n && typeof n === 'object' ? (n.id ?? n) : n))
    const edgeIds = (selectedEdgesList.value || []).map(e => (e && typeof e === 'object' ? (e.id ?? e) : e))

    const nodesPayload = nodeIds.map((nid) => {
      let meta = {}
      try { meta = nodesDataSet.value ? (nodesDataSet.value.get(nid) || {}) : {} } catch {}
      return {
        id: meta.id || nid,
        key: meta._key || meta.key || null,
        label: meta.label || meta.name || null,
      }
    })

    const edgesPayload = edgeIds.map((eid) => {
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
      timestamp: Date.now(),
    }

    console.log(`Sending selection: ${nodesPayload.length} nodes, ${edgesPayload.length} edges`)
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
      
      // НЕ очищаем скрытые элементы при expand операциях
      // Это позволяет правильно восстанавливать состояние при отмене
      
      let addedNodesCount = 0
      let addedEdgesCount = 0
      
      // Добавить узлы, которых еще нет
      for (const node of newNodes) {
        // Проверить, есть ли узел в allNodesData
        const exists = allNodesData.value.find(n => n.id === node.id)
        if (!exists) {
          allNodesData.value.push(node)
        }
        
        // Убрать из скрытых и добавить в визуализацию
        if (hiddenNodes.value.has(node.id)) {
          hiddenNodes.value.delete(node.id)
        }
        
        // Проверить, есть ли в DataSet
        const existsInDataSet = nodesDataSet.value.get(node.id)
        if (!existsInDataSet) {
          nodesDataSet.value.add(node)
          addedNodesCount++
        }
      }
      
      // Добавить рёбра, которых еще нет
      for (const edge of newEdges) {
        const exists = allEdgesData.value.find(e => e.id === edge.id)
        if (!exists) {
          allEdgesData.value.push(edge)
        }
        
        if (hiddenEdges.value.has(edge.id)) {
          hiddenEdges.value.delete(edge.id)
        }
        
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
      
      // НЕ очищаем скрытые элементы при expand операциях
      // Это позволяет правильно восстанавливать состояние при отмене
      
      let addedNodesCount = 0
      let addedEdgesCount = 0
      
      for (const node of newNodes) {
        const exists = allNodesData.value.find(n => n.id === node.id)
        if (!exists) {
          allNodesData.value.push(node)
        }
        
        if (hiddenNodes.value.has(node.id)) {
          hiddenNodes.value.delete(node.id)
        }
        
        const existsInDataSet = nodesDataSet.value.get(node.id)
        if (!existsInDataSet) {
          nodesDataSet.value.add(node)
          addedNodesCount++
        }
      }
      
      for (const edge of newEdges) {
        const exists = allEdgesData.value.find(e => e.id === edge.id)
        if (!exists) {
          allEdgesData.value.push(edge)
        }
        
        if (hiddenEdges.value.has(edge.id)) {
          hiddenEdges.value.delete(edge.id)
        }
        
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
        if (allEdgesData.value) {
          for (const edge of allEdgesData.value) {
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
      
      // Добавить в скрытые (конвертируем в числа для консистентности)
      nodeIds.forEach(id => hiddenNodes.value.add(parseInt(id)))
      edgeIds.forEach(id => hiddenEdges.value.add(parseInt(id)))
      
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
      
      // Рекурсивная клиентская логика для поиска всех связанных узлов
      const nodeIds = [nodeId]
      const edgeIds = []
      const processedNodes = new Set([nodeId])
      
      // Рекурсивная функция для поиска всех родительских узлов
      const findParentsRecursively = (currentNodeId) => {
        if (allEdgesData.value) {
          for (const edge of allEdgesData.value) {
            // Проверяем, является ли узел концом ребра (входящие связи)
            const edgeEndId = edge.to || edge.end_id
            if (edgeEndId == currentNodeId) {
              const parentNodeId = edge.from || edge.start_id
              if (parentNodeId && !processedNodes.has(parentNodeId)) {
                nodeIds.push(parentNodeId)
                processedNodes.add(parentNodeId)
                // Рекурсивно ищем родителей этого узла
                findParentsRecursively(parentNodeId)
              }
              if (edge.id || edge._id) {
                edgeIds.push(edge.id || edge._id)
              }
            }
          }
        }
      }
      
      // Запускаем рекурсивный поиск
      findParentsRecursively(nodeId)
      
      // Добавить в скрытые (конвертируем в числа для консистентности)
      nodeIds.forEach(id => hiddenNodes.value.add(parseInt(id)))
      edgeIds.forEach(id => hiddenEdges.value.add(parseInt(id)))
      
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
      hiddenNodes: Array.from(hiddenNodes.value), // Сохранить скрытые узлы
      hiddenEdges: Array.from(hiddenEdges.value), // Сохранить скрытые рёбра
      isHideOperation: hiddenNodes.value.size > 0, // Флаг типа операции
      timestamp: now
    }
    
    // Проверить, не является ли это состояние дубликатом
    if (lastSavedState.value && 
        lastSavedState.value.startNode === currentState.startNode &&
        lastSavedState.value.depth === currentState.depth &&
        lastSavedState.value.project === currentState.project &&
        lastSavedState.value.nodeCount === currentState.nodeCount &&
        lastSavedState.value.edgeCount === currentState.edgeCount &&
        JSON.stringify(lastSavedState.value.hiddenNodes) === JSON.stringify(currentState.hiddenNodes) &&
        JSON.stringify(lastSavedState.value.hiddenEdges) === JSON.stringify(currentState.hiddenEdges)) {
      console.log('Пропущено дублирующее состояние')
      return
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
    
    // Сохранить как последнее состояние
    lastSavedState.value = currentState
    lastSaveTime.value = now
    
    const displayName = currentState.startNode || 'всё'
    console.log(`Сохранено состояние: ${displayName} (${currentState.nodeCount} узлов, ${currentState.edgeCount} рёбер)`)
    console.log(`История: ${viewHistory.value.length} состояний, текущий индекс: ${currentHistoryIndex.value}`)
  }
  
  /**
   * Восстановление состояния из истории
   */
  const restoreState = (state) => {
    console.log(`Восстановление состояния: ${state.startNode || 'всё'} (${state.nodeCount} узлов)`)
    isRestoringFromHistory.value = true // Включить флаг восстановления
    startNode.value = state.startNode
    depth.value = state.depth
    project.value = state.project
    lastSavedState.value = null // Сбросить последнее состояние
    
    // Восстановить состояние визуализации напрямую
    restoreVisualizationState(state)
    
    // Выключить флаг после завершения восстановления
    setTimeout(() => {
      isRestoringFromHistory.value = false
      console.log('Восстановление завершено, флаг сброшен')
    }, 500) // Увеличено время до 500ms
  }
  
  /**
   * Восстановление состояния визуализации напрямую
   * Вместо загрузки из API восстанавливаем состояние DataSet
   */
  const restoreVisualizationState = (state) => {
    console.log('Восстановление визуализации напрямую')
    
    // Восстановить состояние скрытых элементов
    if (state.hiddenNodes) {
      hiddenNodes.value.clear()
      state.hiddenNodes.forEach(nodeId => hiddenNodes.value.add(nodeId))
    }
    if (state.hiddenEdges) {
      hiddenEdges.value.clear()
      state.hiddenEdges.forEach(edgeId => hiddenEdges.value.add(edgeId))
    }
    
    // Очистить текущую визуализацию
    if (nodesDataSet.value) {
      nodesDataSet.value.clear()
    }
    if (edgesDataSet.value) {
      edgesDataSet.value.clear()
    }
    
    // Используем сохранённый флаг типа операции
    const isHideOperation = state.isHideOperation || false
    
    if (isHideOperation) {
      // Для hide операций фильтруем по скрытым элементам
      const visibleNodes = allNodesData.value.filter(node => !hiddenNodes.value.has(node.id))
      const visibleEdges = allEdgesData.value.filter(edge => !hiddenEdges.value.has(edge.id))
      
      if (visibleNodes.length > 0) {
        nodesDataSet.value.add(visibleNodes)
      }
      if (visibleEdges.length > 0) {
        edgesDataSet.value.add(visibleEdges)
      }
      
      console.log(`Восстановлено (hide): ${visibleNodes.length} видимых узлов, ${visibleEdges.length} видимых рёбер`)
      console.log(`Скрыто: ${hiddenNodes.value.size} узлов, ${hiddenEdges.value.size} рёбер`)
    } else {
      // Для expand операций показываем первые N узлов
      const nodesToShow = allNodesData.value.slice(0, state.nodeCount)
      const edgesToShow = allEdgesData.value.slice(0, state.edgeCount)
      
      if (nodesToShow.length > 0) {
        nodesDataSet.value.add(nodesToShow)
      }
      if (edgesToShow.length > 0) {
        edgesDataSet.value.add(edgesToShow)
      }
      
      console.log(`Восстановлено (expand): ${nodesToShow.length} узлов, ${edgesToShow.length} рёбер`)
    }
  }
  
  /**
   * Показать весь граф
   */
  const showAllGraph = () => {
    startNode.value = ''  // Очистить стартовый узел
    loadGraph()          // Загрузить весь граф (состояние сохранится автоматически)
  }
  
  /**
   * Отменить последнее изменение отображения
   */
  const undoView = () => {
    if (canUndo.value) {
      console.log(`Отмена: текущий индекс ${currentHistoryIndex.value}, история ${viewHistory.value.length} состояний`)
      console.log('История состояний:', viewHistory.value.map(s => `${s.startNode || 'всё'} (${s.nodeCount} узлов)`))
      
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
    clearSelection,
    
    // Expand/Hide actions
    expandNodeChildren,
    expandNodeParents,
    hideNodeWithChildren,
    hideNodeWithParents,
    
    // Visibility state
    allNodesData,
    allEdgesData,
    hiddenNodes,
    hiddenEdges,
    visibleNodesCount,
    visibleEdgesCount,
    
    // History management
    viewHistory,
    currentHistoryIndex,
    canUndo,
    canRedo,
    saveCurrentState,
    showAllGraph,
    undoView,
    redoView
  }

  // Экспорт для внешнего вызова (MCP) – безопасно
  if (typeof window !== 'undefined') {
    window.$graphStore = {
      sendSelectionToServer: api.sendSelectionToServer
    }
  }

  return api
})

