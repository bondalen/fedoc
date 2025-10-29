/**
 * Утилиты для применения оформления узлов и рёбер
 */

import visualizationConfig from '@/config/visualization.json'

/**
 * Применить оформление к узлу
 * @param {Object} node - узел с полями {id, key, label, type}
 * @param {string} theme - 'dark' или 'light'
 * @param {boolean} isSelected - выделен ли узел
 * @param {boolean} isHovered - наведён ли курсор
 * @returns {Object} узел с применённым оформлением
 */
export const applyNodeVisualization = (node, theme, isSelected = false, isHovered = false) => {
  const type = getNodeType(node.key)
  const typeConfig = visualizationConfig.nodes[type] || visualizationConfig.default.nodes
  const themeConfig = typeConfig[theme]
  
  // Базовое оформление
  let visualNode = {
    ...node,
    color: {
      background: node.color?.background || themeConfig.color,
      border: node.color?.border || themeConfig.border,
      highlight: {
        background: node.color?.background || themeConfig.color,
        border: isSelected ? visualizationConfig.states.selected.border : 
                isHovered ? visualizationConfig.states.hover.border : 
                (node.color?.border || themeConfig.border)
      },
      hover: {
        background: node.color?.background || themeConfig.color,
        border: visualizationConfig.states.hover.border
      }
    },
    shape: node.shape || themeConfig.shape,
    font: {
      color: node.font?.color || themeConfig.font.color,
      size: node.font?.size || themeConfig.font.size
    },
    borderWidth: node.borderWidth || (isSelected ? visualizationConfig.states.selected.width : 1),
    borderWidthSelected: visualizationConfig.states.selected.width
  }
  
  return visualNode
}

/**
 * Применить оформление к ребру
 * @param {Object} edge - ребро с полями {id, from, to, type}
 * @param {string} theme - 'dark' или 'light'
 * @param {boolean} isSelected - выделено ли ребро
 * @param {boolean} isHovered - наведён ли курсор
 * @returns {Object} ребро с применённым оформлением
 */
export const applyEdgeVisualization = (edge, theme, isSelected = false, isHovered = false) => {
  const edgeType = edge.type || 'uses'
  const edgeConfig = visualizationConfig.edges[edgeType] || visualizationConfig.edges.uses
  const defaultConfig = visualizationConfig.default.edges[theme]
  
  let visualEdge = {
    ...edge,
    color: {
      color: edgeConfig.color,
      highlight: isSelected ? visualizationConfig.states.selected.border : 
                 isHovered ? visualizationConfig.states.hover.border : edgeConfig.color,
      hover: visualizationConfig.states.hover.border
    },
    width: defaultConfig.width,
    font: {
      color: defaultConfig.font.color,
      size: defaultConfig.font.size,
      strokeWidth: defaultConfig.font.strokeWidth
    },
    dashes: edgeConfig.dashes
  }
  
  return visualEdge
}

/**
 * Определить тип узла по ключу
 * @param {string} key - ключ узла (например, "c:backend", "t:spring-boot", "v:java@21")
 * @returns {string} тип узла
 */
export const getNodeType = (key) => {
  if (!key) return 'default'
  
  if (key.startsWith('c:')) return 'category'
  if (key.startsWith('t:')) return 'technology'
  if (key.startsWith('v:')) return 'version'
  
  return 'default'
}

/**
 * Применить оформление к массиву узлов
 * @param {Array} nodes - массив узлов
 * @param {string} theme - тема
 * @param {Array} selectedNodeIds - ID выделенных узлов
 * @param {Array} hoveredNodeIds - ID узлов под курсором
 * @returns {Array} массив узлов с оформлением
 */
export const applyNodesVisualization = (nodes, theme, selectedNodeIds = [], hoveredNodeIds = []) => {
  return nodes.map(node => {
    const isSelected = selectedNodeIds.includes(node.id)
    const isHovered = hoveredNodeIds.includes(node.id)
    return applyNodeVisualization(node, theme, isSelected, isHovered)
  })
}

/**
 * Применить оформление к массиву рёбер
 * @param {Array} edges - массив рёбер
 * @param {string} theme - тема
 * @param {Array} selectedEdgeIds - ID выделенных рёбер
 * @param {Array} hoveredEdgeIds - ID рёбер под курсором
 * @returns {Array} массив рёбер с оформлением
 */
export const applyEdgesVisualization = (edges, theme, selectedEdgeIds = [], hoveredEdgeIds = []) => {
  return edges.map(edge => {
    const isSelected = selectedEdgeIds.includes(edge.id)
    const isHovered = hoveredEdgeIds.includes(edge.id)
    return applyEdgeVisualization(edge, theme, isSelected, isHovered)
  })
}
