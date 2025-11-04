/**
 * Утилита для экспорта графа в SVG
 * Использует данные из vis-network и стили из visualization.json
 */

import visualizationConfig from '@/config/visualization.json'
import { getNodeType } from './visualization.js'

const PADDING = 48 // Отступ от краёв в пикселях
const ARROW_SIZE = 8 // Размер стрелки

/**
 * Получить размеры узла из конфига
 */
function getNodeDimensions(nodeType, shape, theme = 'light') {
  const typeConfig = visualizationConfig.nodes[nodeType] || visualizationConfig.default.nodes
  const themeConfig = typeConfig[theme]
  const defaultConfig = visualizationConfig.default.nodes[theme]
  const sizeConfig = themeConfig.size || defaultConfig.size || {}
  
  if (shape === 'box') {
    return {
      width: sizeConfig.width || 120,
      height: sizeConfig.height || 36,
      borderRadius: sizeConfig.borderRadius || 6,
      borderWidth: sizeConfig.borderWidth || 1
    }
  } else if (shape === 'circle') {
    return {
      size: sizeConfig.size || 36,
      borderWidth: sizeConfig.borderWidth || 1
    }
  } else if (shape === 'diamond') {
    return {
      size: sizeConfig.size || 24,
      borderWidth: sizeConfig.borderWidth || 1
    }
  }
  
  return { width: 120, height: 36, borderRadius: 6, borderWidth: 1 }
}

/**
 * Создать SVG-маркер стрелки
 */
function createArrowMarker(id, color) {
  return `
    <marker
      id="${id}"
      viewBox="0 0 10 10"
      refX="9"
      refY="5"
      markerWidth="${ARROW_SIZE}"
      markerHeight="${ARROW_SIZE}"
      orient="auto"
    >
      <polygon
        points="0,0 10,5 0,10"
        fill="${color}"
        stroke="none"
      />
    </marker>
  `
}

/**
 * Рендерить узел в SVG
 */
function renderNode(node, position, theme = 'light') {
  const nodeType = getNodeType(node.key || node._key)
  const typeConfig = visualizationConfig.nodes[nodeType] || visualizationConfig.default.nodes
  const themeConfig = typeConfig[theme]
  const defaultConfig = visualizationConfig.default.nodes[theme]
  
  const fill = themeConfig.color || defaultConfig.color
  const stroke = themeConfig.border || defaultConfig.border
  const fontColor = themeConfig.font?.color || defaultConfig.font.color
  const fontSize = themeConfig.font?.size || defaultConfig.font.size
  const fontStrokeWidth = themeConfig.font?.strokeWidth || defaultConfig.font?.strokeWidth || 0
  const fontStrokeColor = themeConfig.font?.strokeColor || defaultConfig.font?.strokeColor || 'transparent'
  const label = node.label || node.name || node.id || ''
  const shape = themeConfig.shape || defaultConfig.shape || 'box'
  
  let nodeElement = ''
  let textX = position.x
  let textY = position.y
  
  const dims = getNodeDimensions(nodeType, shape, theme)
  
  switch (shape) {
    case 'box': {
      const width = dims.width
      const height = dims.height
      const radius = dims.borderRadius
      const borderWidth = dims.borderWidth
      nodeElement = `
        <rect
          x="${position.x - width / 2}"
          y="${position.y - height / 2}"
          width="${width}"
          height="${height}"
          rx="${radius}"
          fill="${fill}"
          stroke="${stroke}"
          stroke-width="${borderWidth}"
        />
      `
      break
    }
      
    case 'circle': {
      const radius = dims.size / 2
      const borderWidth = dims.borderWidth
      nodeElement = `
        <circle
          cx="${position.x}"
          cy="${position.y}"
          r="${radius}"
          fill="${fill}"
          stroke="${stroke}"
          stroke-width="${borderWidth}"
        />
      `
      break
    }
      
    case 'diamond': {
      const size = dims.size
      const halfSize = size / 2
      const borderWidth = dims.borderWidth
      nodeElement = `
        <polygon
          points="${position.x},${position.y - halfSize} ${position.x + halfSize},${position.y} ${position.x},${position.y + halfSize} ${position.x - halfSize},${position.y}"
          fill="${fill}"
          stroke="${stroke}"
          stroke-width="${borderWidth}"
        />
      `
      break
    }
      
    default: {
      // Fallback к box
      const w = 120
      const h = 36
      nodeElement = `
        <rect
          x="${position.x - w / 2}"
          y="${position.y - h / 2}"
          width="${w}"
          height="${h}"
          rx="6"
          fill="${fill}"
          stroke="${stroke}"
          stroke-width="${strokeWidth}"
        />
      `
      break
    }
  }
  
  // Текст с обводкой для читаемости
  // Рендерим два слоя: сначала обводка, потом текст поверх, чтобы обводка не перекрывала текст
  let textElement = ''
  if (fontStrokeWidth > 0) {
    // Слой 1: обводка (под текстом)
    textElement += `
      <text
        x="${textX}"
        y="${textY}"
        text-anchor="middle"
        dominant-baseline="middle"
        fill="none"
        stroke="${fontStrokeColor}"
        stroke-width="${fontStrokeWidth}"
        font-size="${fontSize}"
        font-family="sans-serif"
      >${escapeXml(label)}</text>
    `
  }
  // Слой 2: основной текст поверх обводки
  textElement += `
    <text
      x="${textX}"
      y="${textY}"
      text-anchor="middle"
      dominant-baseline="middle"
      fill="${fontColor}"
      font-size="${fontSize}"
      font-family="sans-serif"
    >${escapeXml(label)}</text>
  `
  
  return nodeElement + textElement
}

/**
 * Вычислить точки для кривой Безье
 */
function calculateBezierPoints(fromPos, toPos, roundness = 0.5, forceDirection = 'vertical') {
  const dx = toPos.x - fromPos.x
  const dy = toPos.y - fromPos.y
  const distance = Math.sqrt(dx * dx + dy * dy)
  
  let cp1x, cp1y, cp2x, cp2y
  
  if (forceDirection === 'vertical') {
    // Вертикальное направление - контрольные точки на середине по X
    const midX = (fromPos.x + toPos.x) / 2
    // Используем расстояние между узлами для вычисления смещения контрольных точек
    const controlOffset = distance * roundness * 0.5
    
    // Если движение вниз (dy > 0)
    if (dy > 0) {
      cp1x = midX
      cp1y = fromPos.y + controlOffset
      cp2x = midX
      cp2y = toPos.y - controlOffset
    } else {
      // Движение вверх
      cp1x = midX
      cp1y = fromPos.y - controlOffset
      cp2x = midX
      cp2y = toPos.y + controlOffset
    }
  } else {
    // Горизонтальное направление - контрольные точки на середине по Y
    const midY = (fromPos.y + toPos.y) / 2
    const controlOffset = distance * roundness * 0.5
    
    // Если движение вправо (dx > 0)
    if (dx > 0) {
      cp1x = fromPos.x + controlOffset
      cp1y = midY
      cp2x = toPos.x - controlOffset
      cp2y = midY
    } else {
      // Движение влево
      cp1x = fromPos.x - controlOffset
      cp1y = midY
      cp2x = toPos.x + controlOffset
      cp2y = midY
    }
  }
  
  return { cp1x, cp1y, cp2x, cp2y }
}

/**
 * Рендерить ребро в SVG
 */
function renderEdge(edge, fromPos, toPos, theme = 'light') {
  const edgeType = edge.type || 'uses'
  const edgeConfig = visualizationConfig.edges[edgeType] || visualizationConfig.edges.uses
  const defaultConfig = visualizationConfig.default.edges[theme]
  
  // Получить конфиг кривизны из edges.smooth
  const smoothConfig = (visualizationConfig.edges && visualizationConfig.edges.smooth) || {}
  
  const color = edgeConfig.color || defaultConfig.color
  const width = defaultConfig.width || 2.5
  const dashes = edgeConfig.dashes ? '6 4' : 'none'
  
  // Проверка кривизны - если smoothConfig есть и type cubicBezier, используем кривые
  const useSmooth = smoothConfig && smoothConfig.type === 'cubicBezier'
  const roundness = smoothConfig.roundness || 0.5
  const forceDirection = smoothConfig.forceDirection || 'vertical'
  
  // Вычислить направление для смещения от границы узла
  const dx = toPos.x - fromPos.x
  const dy = toPos.y - fromPos.y
  const length = Math.sqrt(dx * dx + dy * dy)
  
  if (length === 0) return '' // Нулевая длина - пропускаем
  
  const nx = dx / length
  const ny = dy / length
  
  // Смещение от границы узла (приблизительно, учитывая размер узла)
  const offset = 20
  const adjustedFromX = fromPos.x + nx * offset
  const adjustedFromY = fromPos.y + ny * offset
  const adjustedToX = toPos.x - nx * offset
  const adjustedToY = toPos.y - ny * offset
  
  const markerId = `arrow-${color.replace('#', '')}`
  
  if (useSmooth) {
    // Кривая Безье
    const { cp1x, cp1y, cp2x, cp2y } = calculateBezierPoints(
      { x: adjustedFromX, y: adjustedFromY },
      { x: adjustedToX, y: adjustedToY },
      roundness,
      forceDirection
    )
    
    return `
      <path
        d="M ${adjustedFromX},${adjustedFromY} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${adjustedToX},${adjustedToY}"
        stroke="${color}"
        stroke-width="${width}"
        stroke-dasharray="${dashes}"
        fill="none"
        marker-end="url(#${markerId})"
      />
    `
  } else {
    // Прямая линия
    return `
      <line
        x1="${adjustedFromX}"
        y1="${adjustedFromY}"
        x2="${adjustedToX}"
        y2="${adjustedToY}"
        stroke="${color}"
        stroke-width="${width}"
        stroke-dasharray="${dashes}"
        marker-end="url(#${markerId})"
      />
    `
  }
}

/**
 * Экранировать XML символы
 */
function escapeXml(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/**
 * Экспортировать граф в SVG
 * @param {Object} network - объект vis-network
 * @param {Object} nodesDataSet - DataSet с узлами
 * @param {Object} edgesDataSet - DataSet с рёбрами
 * @param {string} theme - тема ('light' или 'dark')
 * @returns {string} SVG содержимое
 */
export function exportGraphToSVG(network, nodesDataSet, edgesDataSet, theme = 'light') {
  if (!network || !nodesDataSet || !edgesDataSet) {
    console.error('exportGraphToSVG: missing required parameters')
    return ''
  }
  
  // Получить все узлы и рёбра
  const allNodes = nodesDataSet.get()
  const allEdges = edgesDataSet.get()
  
  if (allNodes.length === 0) {
    console.warn('exportGraphToSVG: no nodes to export')
    return ''
  }
  
  // Получить позиции всех узлов
  const nodeIds = allNodes.map(n => n.id)
  const positions = network.getPositions(nodeIds)
  
  // Вычислить bounding box
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  
  for (const nodeId of nodeIds) {
    const pos = positions[nodeId]
    if (pos) {
      minX = Math.min(minX, pos.x)
      maxX = Math.max(maxX, pos.x)
      minY = Math.min(minY, pos.y)
      maxY = Math.max(maxY, pos.y)
    }
  }
  
  // Добавить отступ и максимальный размер узла
  const maxNodeSize = 60 // консервативная оценка
  minX -= maxNodeSize + PADDING
  maxX += maxNodeSize + PADDING
  minY -= maxNodeSize + PADDING
  maxY += maxNodeSize + PADDING
  
  const width = maxX - minX
  const height = maxY - minY
  
  // Собрать уникальные цвета рёбер для маркеров
  const edgeColors = new Set()
  for (const edge of allEdges) {
    const edgeType = edge.type || 'uses'
    const edgeConfig = visualizationConfig.edges[edgeType] || visualizationConfig.edges.uses
    const color = edgeConfig.color || visualizationConfig.default.edges[theme].color
    edgeColors.add(color)
  }
  
  // Генерировать маркеры стрелок
  const markers = Array.from(edgeColors)
    .map(color => createArrowMarker(`arrow-${color.replace('#', '')}`, color))
    .join('\n')
  
  // Рендерить рёбра
  const edgesSVG = allEdges
    .map(edge => {
      const fromPos = positions[edge.from]
      const toPos = positions[edge.to]
      if (!fromPos || !toPos) return ''
      
      // Сместить координаты с учётом padding и смещения bbox
      const adjustedFromPos = {
        x: fromPos.x - minX,
        y: fromPos.y - minY
      }
      const adjustedToPos = {
        x: toPos.x - minX,
        y: toPos.y - minY
      }
      
      return renderEdge(edge, adjustedFromPos, adjustedToPos, theme)
    })
    .filter(svg => svg !== '')
    .join('\n')
  
  // Рендерить узлы
  const nodesSVG = allNodes
    .map(node => {
      const pos = positions[node.id]
      if (!pos) return ''
      
      // Сместить координаты с учётом padding и смещения bbox
      const adjustedPos = {
        x: pos.x - minX,
        y: pos.y - minY
      }
      
      return renderNode(node, adjustedPos, theme)
    })
    .filter(svg => svg !== '')
    .join('\n')
  
  // Собрать полный SVG
  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    ${markers}
  </defs>
  <g>
    <!-- Рёбра (под узлами) -->
    ${edgesSVG}
    
    <!-- Узлы (поверх рёбер) -->
    ${nodesSVG}
  </g>
</svg>`
  
  return svg
}

/**
 * Сохранить SVG в файл
 */
export function downloadSVG(svgContent, filename = 'graph.svg') {
  const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

