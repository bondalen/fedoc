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

// Опции для vis-network
const options = {
  nodes: {
    shape: 'box',
    margin: 10,
    font: {
      size: 16,
      face: 'Arial, sans-serif',
      color: '#e0e0e0',
      bold: {
        color: '#ffffff'
      }
    },
    color: {
      background: '#2d3748',
      border: '#4a5568',
      highlight: {
        background: '#4299e1',
        border: '#63b3ed'
      },
      hover: {
        background: '#3a4a5e',
        border: '#5a6a88'
      }
    },
    borderWidth: 1,
    borderWidthSelected: 2,
    shadow: {
      enabled: true,
      color: 'rgba(0,0,0,0.3)',
      size: 5,
      x: 2,
      y: 2
    }
  },
  edges: {
    arrows: {
      to: {
        enabled: true,
        scaleFactor: 0.5
      }
    },
    color: {
      color: '#B0BEC5',
      highlight: '#4299e1',
      hover: '#64B5F6',
      inherit: false
    },
    width: 1,
    smooth: {
      enabled: true,
      type: 'cubicBezier',
      forceDirection: 'vertical',
      roundness: 0.5
    },
    font: {
      size: 12,
      color: '#e0e0e0',
      strokeWidth: 2,
      strokeColor: '#000',
      align: 'middle'
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
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
#graph {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #1e1e1e;
  border: 1px solid #333;
  transition: right 0.3s ease;
}

#graph.with-panel {
  right: 420px;
}
</style>

