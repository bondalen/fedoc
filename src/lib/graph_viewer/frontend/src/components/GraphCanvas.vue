<template>
  <div 
    id="graph" 
    ref="graphContainer"
    :class="{ 'with-panel': store.showDetails }"
  ></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { useGraphStore } from '@/stores/graph'

const store = useGraphStore()
const graphContainer = ref(null)
let network = null

// Emit для передачи события контекстного меню наверх
const emit = defineEmits(['show-context-menu'])

// Опции для vis-network (только статичные, цвета задаются в applyTheme)
const options = {
  nodes: {
    shape: 'box',
    margin: 10,
    borderWidth: 1,
    borderWidthSelected: 2
  },
  edges: {
    arrows: {
      to: {
        enabled: true,
        scaleFactor: 0.5
      }
    },
    width: 1,
    smooth: {
      enabled: true,
      type: 'cubicBezier',
      forceDirection: 'vertical',
      roundness: 0.5
    },
    shadow: {
      enabled: false
    }
  },
  physics: {
    enabled: true,
    solver: 'hierarchicalRepulsion',
    hierarchicalRepulsion: {
      nodeDistance: 160,
      springLength: 160,
      damping: 0.45,
      avoidOverlap: 1
    },
    stabilization: {
      enabled: true,
      iterations: 800,
      updateInterval: 25,
      fit: true
    }
  },
  interaction: {
    hover: true,
    tooltipDelay: 200,
    navigationButtons: true,
    keyboard: true,
    zoomView: true,
    dragView: true,
    multiselect: true,  // Включить множественный выбор (Ctrl+Click)
    selectConnectedEdges: false  // Не выбирать связанные рёбра автоматически
  },
  layout: {
    hierarchical: {
      enabled: true,
      direction: 'UD',
      sortMethod: 'directed',
      levelSeparation: 140,
      nodeSpacing: 180,
      treeSpacing: 240,
      blockShifting: true,
      edgeMinimization: true,
      parentCentralization: true
    }
  }
}

/**
 * Инициализация vis-network
 */
const initNetwork = () => {
  if (!graphContainer.value) {
    console.error('GraphCanvas: контейнер не найден')
    return
  }
  
  // Создание DataSet для узлов и рёбер
  const nodesDataSet = new DataSet([])
  const edgesDataSet = new DataSet([])
  
  // Создание сети
  network = new Network(
    graphContainer.value,
    {
      nodes: nodesDataSet,
      edges: edgesDataSet
    },
    options
  )
  
  // Регистрация обработчиков событий
  
  // Обработка изменения выборки (узлы и/или рёбра)
  network.on('select', async (params) => {
    const selectedNodes = params.nodes || []
    const selectedEdges = params.edges || []
    
    console.log(`Selection changed: ${selectedNodes.length} nodes, ${selectedEdges.length} edges`)
    
    // Обновить выборку в store
    await store.updateSelectedNodes(selectedNodes)
    await store.updateSelectedEdges(selectedEdges)
    
    // Показать панель деталей для первого выбранного объекта (старое поведение)
    if (selectedNodes.length > 0) {
      const firstNodeId = selectedNodes[0]
      await store.selectNode(firstNodeId)
    } else if (selectedEdges.length > 0) {
      const firstEdgeId = selectedEdges[0]
      await store.selectEdge(firstEdgeId)
    }
  })
  
  // Обработка клика на пустом месте (снятие выделения)
  network.on('deselectNode', (params) => {
    // Проверить, есть ли еще выбранные объекты
    const currentNodes = network.getSelectedNodes()
    const currentEdges = network.getSelectedEdges()
    
    if (currentNodes.length === 0 && currentEdges.length === 0) {
      console.log('All deselected, clearing selection')
      store.clearSelection()
      // Можно также закрыть панель деталей
      // store.closeDetails()
    }
  })
  
  network.on('deselectEdge', (params) => {
    // Проверить, есть ли еще выбранные объекты
    const currentNodes = network.getSelectedNodes()
    const currentEdges = network.getSelectedEdges()
    
    if (currentNodes.length === 0 && currentEdges.length === 0) {
      console.log('All deselected, clearing selection')
      store.clearSelection()
    }
  })
  
  network.on('stabilizationProgress', (params) => {
    // Можно отображать прогресс стабилизации
    const progress = Math.round((params.iterations / params.total) * 100)
    console.log(`Стабилизация: ${progress}%`)
  })
  
  network.on('stabilizationIterationsDone', () => {
    console.log('Стабилизация завершена')
    // Отключить физику после стабилизации для повышения производительности
    network.setOptions({ physics: { enabled: false } })
  })
  
  // Тултип при наведении на узел
  network.on('hoverNode', (params) => {
    const nodeId = params.node
    const nodeData = nodesDataSet.get(nodeId)
    
    if (nodeData) {
      // Создаём тултип с информацией об узле
      let tooltipText = nodeData.label || nodeData.id
      if (nodeData.title) {
        tooltipText = nodeData.title
      } else if (nodeData.name) {
        tooltipText = `${nodeData.label || nodeData.id}\n${nodeData.name}`
      }
      
      // vis-network автоматически показывает title как тултип
      network.canvas.body.container.title = tooltipText
    }
  })
  
  network.on('blurNode', () => {
    network.canvas.body.container.title = ''
  })
  
  // Тултип при наведении на ребро
  network.on('hoverEdge', (params) => {
    const edgeId = params.edge
    const edgeData = edgesDataSet.get(edgeId)
    
    if (edgeData) {
      let tooltipText = edgeData.label || 'Связь'
      if (edgeData.title) {
        tooltipText = edgeData.title
      } else if (edgeData.type) {
        tooltipText = `Тип: ${edgeData.type}`
        if (edgeData.label) {
          tooltipText = `${edgeData.label} (${edgeData.type})`
        }
      }
      
      network.canvas.body.container.title = tooltipText
    }
  })
  
  network.on('blurEdge', () => {
    network.canvas.body.container.title = ''
  })
  
  // Обработка правого клика (контекстное меню)
  network.on('oncontext', (params) => {
    params.event.preventDefault()  // Отключить стандартное браузерное меню
    
    const nodeId = network.getNodeAt(params.pointer.DOM)
    
    if (nodeId) {
      // Получить позицию клика на странице
      const domPosition = params.pointer.DOM
      
      // Получить позицию canvas на странице
      const canvasRect = graphContainer.value.getBoundingClientRect()
      
      // Вычислить абсолютную позицию
      const position = {
        x: canvasRect.left + domPosition.x,
        y: canvasRect.top + domPosition.y
      }
      
      console.log(`Context menu on node: ${nodeId} at (${position.x}, ${position.y})`)
      
      // Передать событие наверх в GraphViewer
      emit('show-context-menu', { nodeId, position })
    }
  })
  
  // Сохранение ссылок в store
  store.setNetwork(network, nodesDataSet, edgesDataSet)
  
  console.log('GraphCanvas: сеть инициализирована')
}

/**
 * Очистка при размонтировании
 */
const cleanup = () => {
  if (network) {
    network.destroy()
    network = null
  }
}

// Lifecycle hooks
onMounted(() => {
  initNetwork()
  // Загрузить данные после инициализации
  store.loadNodes()
  
  // Добавить обработчик горячих клавиш
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  cleanup()
  // Удалить обработчик горячих клавиш
  document.removeEventListener('keydown', handleKeyDown)
})

// Обработчик горячих клавиш
const handleKeyDown = (e) => {
  if (e.ctrlKey) {
    switch(e.key) {
      case 'a':
        e.preventDefault()
        store.showAllGraph()
        break
      case 'z':
        e.preventDefault()
        store.undoView()
        break
      case 'y':
        e.preventDefault()
        store.redoView()
        break
    }
  }
}
</script>

<style scoped>
#graph {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--canvas-bg, #1e1e1e) !important;
  border: 1px solid var(--border-color, #333);
  transition: right 0.3s ease;
}

/* 🎯 ПРИНУДИТЕЛЬНЫЙ ФОН для canvas элементов */
#graph canvas {
  background: var(--canvas-bg, #1e1e1e) !important;
}

/* 🎯 Специальные стили для тем */
.theme-light #graph {
  background: #ffffff !important;
}

.theme-light #graph canvas {
  background: #ffffff !important;
}

.theme-dark #graph {
  background: #1e1e1e !important;
}

.theme-dark #graph canvas {
  background: #1e1e1e !important;
}

#graph.with-panel {
  right: 420px;
}
</style>

