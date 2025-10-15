# Архитектура фронтенда Graph Viewer

## 📦 Текущая структура (Alpine.js + Vite)

### Стек технологий
- **Alpine.js** - реактивный фреймворк для UI
- **Vite** - сборщик и dev server
- **vis-network** - библиотека для визуализации графов
- **vis-data** - DataSet для управления данными графа

### Файловая структура
```
frontend/
├── index.html          # Главная страница
├── src/
│   ├── main.js         # ОСНОВНОЙ КОМПОНЕНТ (весь код)
│   └── style.css       # Стили
├── package.json
└── vite.config.js
```

## 🎯 Текущая архитектура: МОНОЛИТ

**Один компонент `graphViewer()`** содержит всё:
- Управление состоянием (nodes, edges, theme, etc.)
- Инициализация vis-network
- Загрузка данных через API
- Рендеринг JSON объектов
- Панель деталей
- Панель полного текста
- Event handlers

### Проблемы монолита:
1. ❌ **Сложность поддержки** - 500+ строк в одном файле
2. ❌ **Нет переиспользования** - логика не разделена
3. ❌ **Проблемы с реактивностью** - динамический HTML через строки
4. ❌ **Сложная отладка** - всё в одном контексте

## 🏗️ Предлагаемая компонентная архитектура

### Вариант 1: Alpine.js компоненты через `Alpine.data()`

```javascript
// src/components/graphViewer.js
Alpine.data('graphViewer', () => ({
  network: null,
  nodes: [],
  edges: [],
  // ... основная логика графа
}))

// src/components/detailsPanel.js
Alpine.data('detailsPanel', () => ({
  selectedObject: null,
  isOpen: false,
  // ... логика панели деталей
}))

// src/components/fullTextPanel.js
Alpine.data('fullTextPanel', () => ({
  text: '',
  isVisible: false,
  show(text) { ... },
  hide() { ... }
}))
```

**Преимущества:**
- ✅ Разделение ответственности
- ✅ Переиспользование компонентов
- ✅ Простая отладка
- ✅ Минимальный рефакторинг

**Недостатки:**
- ⚠️ Alpine.js не лучший для сложных SPA
- ⚠️ Проблемы с динамическим HTML остаются

### Вариант 2: Полноценный компонентный фреймворк (React/Vue)

```jsx
// src/components/GraphViewer.jsx
function GraphViewer() {
  const [nodes, setNodes] = useState([])
  return <div>
    <Controls />
    <Graph nodes={nodes} />
    <DetailsPanel />
  </div>
}

// src/components/DetailsPanel.jsx
function DetailsPanel({ object }) {
  return <div className="details-panel">
    <JSONRenderer object={object} />
    <FullTextPanel />
  </div>
}
```

**Преимущества:**
- ✅ Полная компонентная структура
- ✅ Реактивность "из коробки"
- ✅ Богатая экосистема
- ✅ TypeScript поддержка

**Недостатки:**
- ❌ Большой рефакторинг
- ❌ Увеличение размера бандла
- ❌ Требует больше времени

## 🎯 Рекомендация

### Для текущего проекта: **Alpine.js с компонентами**

**Этапы:**
1. **Разбить `main.js` на модули:**
   ```
   src/
   ├── components/
   │   ├── graphViewer.js    # Основной граф
   │   ├── detailsPanel.js   # Панель деталей
   │   ├── fullTextPanel.js  # Панель текста
   │   └── jsonRenderer.js   # Рендеринг JSON
   ├── utils/
   │   ├── api.js            # API запросы
   │   └── formatters.js     # Форматирование данных
   └── main.js               # Инициализация
   ```

2. **Переписать рендеринг JSON** на Alpine.js шаблоны вместо строк

3. **Использовать Alpine.js директивы** вместо `onclick`

### В будущем: **React/Vue для MCP server**

Когда интегрируем с MCP-сервером, стоит пересмотреть и использовать React/Vue для:
- Сложной навигации
- Rich interactions
- State management (Zustand/Pinia)

## 📝 Текущие проблемы с реактивностью

**Проблема:** Динамический HTML через `x-html` не поддерживает Alpine.js директивы

**Текущее решение:** Event delegation
```javascript
document.addEventListener('click', (e) => {
  const target = e.target.closest('.text-truncated')
  if (target) {
    this.openFullText(target.dataset.fullText)
  }
})
```

**Правильное решение:** Компоненты Alpine.js с шаблонами
```html
<div x-for="(value, key) in object">
  <span x-text="key"></span>
  <span x-show="!isTruncated(value)" x-text="value"></span>
  <span x-show="isTruncated(value)" 
        @click="openFullText(value)" 
        x-text="truncate(value)"></span>
</div>
```

---

**Вывод:** Текущая архитектура - монолит. Рекомендуется разбить на Alpine.js компоненты для упрощения разработки.

