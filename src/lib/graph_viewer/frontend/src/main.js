import Alpine from 'alpinejs';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import './style.css';

// API базовый URL (для разработки - текущий хост, для продакшена - localhost:8899)
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8899'
  : '';

// Глобальная ссылка на компонент
let graphViewerInstance = null;

// Alpine.js компонент для Graph Viewer
window.graphViewer = function() {
  const instance = {
    // Состояние
    nodes: [],
    startNode: 'canonical_nodes/c:backend',
    depth: 5,
    project: '',
    theme: 'dark',
    nodeCount: 0,
    edgeCount: 0,
    showDetails: false,
    selectedObject: null,
    
    // Vis.js network
    network: null,
    nodesDataSet: null,
    edgesDataSet: null,
    
    // Панель деталей
    panelWidth: 420,
    isResizing: false,
    loadedDocs: new Set(),
    
    // Инициализация
    async init() {
      console.log('Initializing Graph Viewer...');
      await this.initNetwork();
      await this.loadNodes();
      await this.loadGraph();
    },
    
    // Инициализация vis-network
    initNetwork() {
      const container = document.getElementById('graph');
      const options = {
        physics: {
          enabled: true,
          solver: 'hierarchicalRepulsion',
          hierarchicalRepulsion: {
            nodeDistance: 160,
            springLength: 160,
            damping: 0.45,
            avoidOverlap: 1
          },
          stabilization: { iterations: 800 }
        },
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            levelSeparation: 140,
            nodeSpacing: 180,
            treeSpacing: 240,
            sortMethod: 'directed',
            edgeMinimization: true,
            blockShifting: true,
            parentCentralization: true
          }
        },
        interaction: {
          navigationButtons: true,
          keyboard: true,
          hover: true
        },
        edges: {
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          smooth: { type: 'cubicBezier', forceDirection: 'vertical' },
          font: { size: 12, align: 'middle' }
        },
        nodes: { font: { size: 16 } }
      };
      
      // Создаём DataSet
      this.nodesDataSet = new DataSet([]);
      this.edgesDataSet = new DataSet([]);
      
      this.network = new Network(container, { 
        nodes: this.nodesDataSet, 
        edges: this.edgesDataSet 
      }, options);
      
      // Обработчик выбора узла/ребра
      this.network.on('select', async (params) => {
        if (params.nodes.length > 0) {
          await this.loadObjectDetails(params.nodes[0]);
        } else if (params.edges.length > 0) {
          await this.loadObjectDetails(params.edges[0]);
        } else {
          this.showDetails = false;
        }
      });
      
      console.log('Network initialized');
    },
    
    // Загрузка списка узлов
    async loadNodes() {
      try {
        const url = `${API_BASE}/nodes${this.project ? '?project=' + this.project : ''}`;
        const res = await fetch(url);
        this.nodes = await res.json();
        console.log(`Loaded ${this.nodes.length} nodes`);
      } catch (e) {
        console.error('Error loading nodes:', e);
      }
    },
    
    // Загрузка графа
    async loadGraph() {
      try {
        const params = new URLSearchParams({
          start: this.startNode,
          depth: this.depth,
          project: this.project,
          theme: this.theme
        });
        
        const url = `${API_BASE}/graph?${params}`;
        const res = await fetch(url);
        const data = await res.json();
        
        // Очищаем старые данные
        this.nodesDataSet.clear();
        this.edgesDataSet.clear();
        
        // Добавляем новые данные
        this.nodesDataSet.add(data.nodes);
        this.edgesDataSet.add(data.edges);
        
        this.nodeCount = data.nodes.length;
        this.edgeCount = data.edges.length;
        
        this.applyTheme();
        
        console.log(`Graph loaded: ${this.nodeCount} nodes, ${this.edgeCount} edges`);
      } catch (e) {
        console.error('Error loading graph:', e);
      }
    },
    
    // Применение темы
    applyTheme() {
      const isDark = this.theme === 'dark';
      document.body.style.background = isDark ? '#111' : '#fff';
      document.body.style.color = isDark ? '#e0e0e0' : '#000';
      
      const labelColor = isDark ? '#E0E0E0' : '#212121';
      const edgeColor = isDark ? '#B0BEC5' : '#424242';
      
      if (this.network) {
        this.network.setOptions({
          nodes: { font: { color: labelColor } },
          edges: {
            font: { color: labelColor, strokeColor: isDark ? '#000' : '#fff' },
            color: { color: edgeColor }
          }
        });
      }
    },
    
    // Подогнать граф
    fitGraph() {
      if (this.network) {
        this.network.fit();
      }
    },
    
    // Загрузка деталей объекта
    async loadObjectDetails(objectId) {
      try {
        const url = `${API_BASE}/object_details?id=${encodeURIComponent(objectId)}`;
        const res = await fetch(url);
        if (res.ok) {
          this.selectedObject = await res.json();
          this.showDetails = true;
          console.log('Loaded object details:', objectId);
        }
      } catch (e) {
        console.error('Error loading object details:', e);
      }
    },
    
    // Закрыть панель деталей
    closeDetails() {
      this.showDetails = false;
      this.selectedObject = null;
      this.loadedDocs.clear();
    },
    
    // Начать изменение размера панели
    startResize(event) {
      this.isResizing = true;
      document.body.style.cursor = 'ew-resize';
      
      const onMouseMove = (e) => {
        if (!this.isResizing) return;
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 200 && newWidth < 800) {
          this.panelWidth = newWidth;
          const panel = document.getElementById('detailsPanel');
          const resizer = document.getElementById('resizer');
          const graph = document.getElementById('graph');
          if (panel) panel.style.width = newWidth + 'px';
          if (resizer) resizer.style.right = newWidth + 'px';
          if (graph) graph.style.right = newWidth + 'px';
        }
      };
      
      const onMouseUp = () => {
        this.isResizing = false;
        document.body.style.cursor = '';
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };
      
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },
    
    // Сокращение имени коллекции
    shortenCollectionName(name) {
      if (name.length <= 4) return name;
      return name.substring(0, 3) + '.' + name.charAt(name.length - 1);
    },
    
    // Форматирование _id с сокращением
    formatDocumentId(fullId) {
      const parts = fullId.split('/');
      if (parts.length !== 2) return fullId;
      const [collection, key] = parts;
      const shortCollection = this.shortenCollectionName(collection);
      return `${shortCollection}/${key}`;
    },
    
    // Проверка на ссылку на документ
    isDocumentRef(str) {
      return typeof str === 'string' && /^[a-zA-Z_][a-zA-Z0-9_]*\/[^\/]+$/.test(str);
    },
    
    // Экранирование HTML
    escapeHtml(str) {
      const div = document.createElement('div');
      div.textContent = str;
      return div.innerHTML;
    },
    
    // Отображение объекта с раскрытием
    renderObject(obj, level = 0, parentPath = '', parentKey = '') {
      if (obj === null) return '<span class="json-null">null</span>';
      if (obj === undefined) return '<span class="json-null">undefined</span>';
      
      const type = typeof obj;
      
      if (type === 'string') {
        if (this.isDocumentRef(obj)) {
          const displayId = this.formatDocumentId(obj);
          const isGraphNode = obj.startsWith('canonical_nodes/');
          
          if (isGraphNode) {
            // Для узлов графа: ссылка + кнопка "Показать"
            return `<span class="doc-link" title="${this.escapeHtml(obj)}" 
                          onclick="window.graphViewerInstance.focusNode('${obj}')">${this.escapeHtml(displayId)}</span>
                    <button class="show-on-graph-btn" onclick="window.graphViewerInstance.focusNode('${obj}')">📍 Показать</button>`;
          } else {
            // Для связанных документов: кнопка разворачивания
            const expandId = `expand_${Math.random().toString(36).substr(2, 9)}`;
            return `<span class="collapse-btn doc-expand-btn" 
                          onclick="window.graphViewerInstance.toggleExpand('${obj}', '${expandId}')">▶</span>
                    <span class="doc-link-readonly" title="${this.escapeHtml(obj)}">${this.escapeHtml(displayId)}</span>
                    <div class="expanded-doc nested" id="${expandId}" style="display: none;"></div>`;
          }
        }
        
        // Обычная строка
        return `<span class="json-string">"${this.escapeHtml(obj)}"</span>`;
      }
      
      if (type === 'number') return `<span class="json-number">${obj}</span>`;
      if (type === 'boolean') return `<span class="json-boolean">${obj}</span>`;
      
      if (Array.isArray(obj)) {
        if (obj.length === 0) return '<span class="json-null">[]</span>';
        
        const id = `arr_${Math.random().toString(36).substr(2, 9)}`;
        let html = `<span class="collapse-btn" onclick="window.graphViewerInstance.toggleCollapse('${id}')">▼</span>[`;
        html += `<div class="nested" id="${id}">`;
        
        obj.forEach((item, idx) => {
          // Проверяем, может ли элемент быть ссылкой на коллекцию
          let renderedItem;
          if (typeof item === 'string' && /^[a-zA-Z0-9_-]+$/.test(item) && item.length < 50) {
            const potentialRef = this.guessCollectionRef(item, parentKey);
            if (potentialRef) {
              const displayId = this.formatDocumentId(potentialRef);
              const isGraphNode = potentialRef.startsWith('canonical_nodes/');
              
              if (isGraphNode) {
                renderedItem = `<span class="doc-link" title="${this.escapeHtml(potentialRef)}" 
                                      onclick="window.graphViewerInstance.focusNode('${potentialRef}')">${this.escapeHtml(displayId)}</span>
                                <button class="show-on-graph-btn" onclick="window.graphViewerInstance.focusNode('${potentialRef}')">📍 Показать</button>`;
              } else {
                const expandId = `expand_${Math.random().toString(36).substr(2, 9)}`;
                renderedItem = `<span class="collapse-btn doc-expand-btn" 
                                      onclick="window.graphViewerInstance.toggleExpand('${potentialRef}', '${expandId}')">▶</span>
                                <span class="doc-link-readonly" title="${this.escapeHtml(potentialRef)}">${this.escapeHtml(displayId)}</span>
                                <div class="expanded-doc nested" id="${expandId}" style="display: none;"></div>`;
              }
            } else {
              renderedItem = this.renderObject(item, level + 1, `${parentPath}[${idx}]`, parentKey);
            }
          } else {
            renderedItem = this.renderObject(item, level + 1, `${parentPath}[${idx}]`, parentKey);
          }
          
          html += `<div class="json-line"><span class="json-key">${idx}:</span> ${renderedItem}</div>`;
        });
        
        html += `</div>]`;
        return html;
      }
      
      if (type === 'object') {
        const keys = Object.keys(obj);
        if (keys.length === 0) return '<span class="json-null">{}</span>';
        
        const id = `obj_${Math.random().toString(36).substr(2, 9)}`;
        let html = `<span class="collapse-btn" onclick="window.graphViewerInstance.toggleCollapse('${id}')">▼</span>{`;
        html += `<div class="nested" id="${id}">`;
        
        keys.forEach(key => {
          html += `<div class="json-line"><span class="json-key">${this.escapeHtml(key)}:</span> ${this.renderObject(obj[key], level + 1, `${parentPath}.${key}`, key)}</div>`;
        });
        
        html += `</div>}`;
        return html;
      }
      
      return String(obj);
    },
    
    // Угадать коллекцию по контексту
    guessCollectionRef(name, parentKey) {
      const knownCollections = {
        'projects': 'projects',
        'rules': 'rules',
        'templates': 'templates',
        'tasks': 'tasks'
      };
      
      const parentLower = (parentKey || '').toLowerCase();
      for (const [hint, collection] of Object.entries(knownCollections)) {
        if (parentLower.includes(hint)) {
          return `${collection}/${name}`;
        }
      }
      
      return null;
    },
    
    // Переключение сворачивания
    toggleCollapse(targetId) {
      const target = document.getElementById(targetId);
      const btn = document.querySelector(`[onclick*="${targetId}"]`);
      if (target && btn) {
        if (target.style.display === 'none') {
          target.style.display = 'block';
          btn.textContent = '▼';
        } else {
          target.style.display = 'none';
          btn.textContent = '▶';
        }
      }
    },
    
    // Переключение разворачивания связанного документа
    async toggleExpand(refId, targetId) {
      const target = document.getElementById(targetId);
      const btn = document.querySelector(`[onclick*="'${refId}'"][onclick*="'${targetId}'"]`);
      
      if (!target || !btn) return;
      
      if (target.style.display === 'none' || target.style.display === '') {
        if (target.innerHTML === '') {
          // Загружаем документ
          btn.textContent = '⏳';
          try {
            const url = `${API_BASE}/object_details?id=${encodeURIComponent(refId)}`;
            const res = await fetch(url);
            if (res.ok) {
              const doc = await res.json();
              this.loadedDocs.add(refId);
              target.innerHTML = this.renderObject(doc, 1, refId, '_root');
              target.style.display = 'block';
              btn.textContent = '▼';
            } else {
              target.innerHTML = '<span style="color: #ff6b6b;">Ошибка загрузки</span>';
              target.style.display = 'block';
              btn.textContent = '▼';
            }
          } catch (err) {
            target.innerHTML = `<span style="color: #ff6b6b;">Ошибка: ${err.message}</span>`;
            target.style.display = 'block';
            btn.textContent = '▼';
          }
        } else {
          // Просто показываем
          target.style.display = 'block';
          btn.textContent = '▼';
        }
      } else {
        // Сворачиваем
        target.style.display = 'none';
        btn.textContent = '▶';
      }
    },
    
    // Фокусировка на узле графа
    focusNode(nodeId) {
      if (this.network) {
        this.network.selectNodes([nodeId]);
        this.network.focus(nodeId, {
          scale: 1.2,
          animation: { duration: 500, easingFunction: 'easeInOutQuad' }
        });
      }
    }
  };
  
  // Сохраняем глобальную ссылку
  window.graphViewerInstance = instance;
  return instance;
};

// Инициализация Alpine.js
Alpine.start();

console.log('Alpine.js started');
