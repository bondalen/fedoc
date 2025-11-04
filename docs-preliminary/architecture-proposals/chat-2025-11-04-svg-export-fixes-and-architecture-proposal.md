# Чат 2025-11-04: Исправление SVG экспорта и предложение архитектуры классов

**Дата**: 2025-11-04  
**Автор**: Александр  
**Статус**: Предложения готовы, ожидают реализации

---

## Краткое содержание

В ходе чата были:
1. Диагностированы и исправлены проблемы с SVG экспортом (нечитаемый текст, отсутствие кривизны рёбер)
2. Обнаружено расхождение стилей между canvas (vis-network) и SVG экспортом
3. Разработано комплексное предложение по архитектуре с иерархией классов
4. Предложена синхронизация классов между фронтендом и бакендом
5. Финализировано решение: хранение метаданных классов в графе (философия fedoc)

---

## Проблемы и исправления

### 1. SVG экспорт: нечитаемый текст

**Проблема**: Обводка текста (stroke) перекрывала заливку (fill), делая текст нечитаемым.

**Решение**: Двойной слой текста в SVG:
- Слой 1: обводка (`fill="none"`, `stroke` с цветом фона узла)
- Слой 2: основной текст (`fill` с цветом текста, без stroke)

**Файл**: `src/lib/graph_viewer/frontend/src/utils/exportToSVG.js` (строки 162-192)

```javascript
// Слой 1: обводка (под текстом)
if (fontStrokeWidth > 0) {
  textElement += `
    <text ... fill="none" stroke="${fontStrokeColor}" stroke-width="${fontStrokeWidth}">
      ${escapeXml(label)}
    </text>
  `
}
// Слой 2: основной текст поверх
textElement += `
  <text ... fill="${fontColor}">
    ${escapeXml(label)}
  </text>
`
```

### 2. SVG экспорт: отсутствие кривизны рёбер

**Проблема**: Рёбра отрисовывались прямыми линиями вместо кривых Безье.

**Решение**: 
- Исправлено чтение конфига `visualizationConfig.edges.smooth`
- Улучшен расчёт контрольных точек кривой Безье с учётом направления движения
- Используется расстояние между узлами для вычисления смещения

**Файл**: `src/lib/graph_viewer/frontend/src/utils/exportToSVG.js` (строки 200-247)

```javascript
function calculateBezierPoints(fromPos, toPos, roundness = 0.5, forceDirection = 'vertical') {
  const distance = Math.sqrt(dx * dx + dy * dy)
  const controlOffset = distance * roundness * 0.5
  
  // Учёт направления движения (вверх/вниз, влево/вправо)
  if (forceDirection === 'vertical') {
    if (dy > 0) {
      cp1y = fromPos.y + controlOffset
      cp2y = toPos.y - controlOffset
    } else {
      cp1y = fromPos.y - controlOffset
      cp2y = toPos.y + controlOffset
    }
  }
  // ... аналогично для horizontal
}
```

---

## Обнаруженная проблема: расхождение стилей

### Источники стилей (конфликт)

Обнаружено, что стили для vis-network берутся из **трёх независимых источников**:

1. **`visualization.json`** — частично используется в `utils/visualization.js`
2. **`GraphCanvas.vue`** — жёстко закодированные опции (строки 24-86)
3. **`stores/graph.js`** — функция `applyTheme()` перезаписывает стили (строки 296-339)

**Последствия**:
- Canvas и SVG выглядят по-разному
- Изменения в `visualization.json` не всегда применяются
- Сложно поддерживать консистентность

**Файлы с проблемами**:
- `src/lib/graph_viewer/frontend/src/components/GraphCanvas.vue`
- `src/lib/graph_viewer/frontend/src/stores/graph.js`
- `src/lib/graph_viewer/frontend/src/utils/visualization.js`

---

## Архитектурные предложения

### Предложение 1: Иерархия классов на фронтенде

См. детальный документ: [`graph-object-class-hierarchy.md`](./graph-object-class-hierarchy.md)

**Основная идея**:
```
GraphObject (базовый)
├── GraphVertex (вершины)
│   ├── ConceptVertex (концепты)
│   ├── TechnologyVertex (технологии)
│   └── VersionVertex (версии)
└── GraphEdge (рёбра)
```

**Ключевые методы**:
- `getVisualStyle(theme)` — получить стиль из конфига
- `toVisNetworkFormat(theme)` — формат для vis-network
- `toSVGFormat(theme, position)` — формат для SVG

**Цель**: Единая точка правды для визуализации.

---

### Предложение 2: Синхронизация фронтенд-бакенд

См. детальный документ: [`frontend-backend-class-sync.md`](./frontend-backend-class-sync.md)

**Основная идея**:
- Единая схема данных `config/schema/graph-schema.yaml`
- Генерация классов для Python и JavaScript из схемы
- Бизнес-классы на обеих сторонах (например, `Project`, `Backend`)

**Структура**:

**Backend (Python)**:
```
models/
├── base.py (GraphObject)
├── vertices/ (GraphVertex, ConceptVertex, ...)
├── edges/ (GraphEdge)
└── business/ (Project, Backend, Frontend)
```

**Frontend (JavaScript)**:
```
models/
├── base.js (GraphObject)
├── vertices/ (GraphVertex, ConceptVertex, ...)
├── edges/ (GraphEdge)
└── business/ (Project, Backend, Frontend)
```

**Инструменты**:
- `tools/generate_classes.py` — генератор из схемы
- `tools/sync_check.py` — проверка синхронности

---

### Предложение 3: Метаданные в графе (ФИНАЛЬНОЕ) ✅

См. детальный документ: [`metadata-in-graph-architecture.md`](./metadata-in-graph-architecture.md)

**Основная идея**: Хранить определения классов в самом графе, а не в YAML.

**Новые типы узлов**:
- `m:*` (meta) — метаданные
- `cls:*` (class-def) — определение класса
- `prop:*` (property-def) — определение свойства
- `meth:*` (method-def) — определение метода
- `rel:*` (relation-def) — определение связи

**Структура в графе**:
```
c:project (Проект fedoc)
  c:meta (Метаданные проекта)
    c:class-system (Система классов)
      cls:GraphObject
        prop:GraphObject.id
        meth:GraphObject.to_dict
      cls:GraphVertex
        prop:GraphVertex.key
        prop:GraphVertex.label
        meth:GraphVertex.infer_type
      cls:Project (Бизнес-класс)
        prop:Project.name
        prop:Project.description
        rel:Project.has_backends
        meth:Project.get_backends
      cls:Backend (Бизнес-класс)
        prop:Backend.framework
        prop:Backend.database
        meth:Backend.get_project
    c:visualization-config
      c:node-styles
      c:edge-styles
    c:api-contract
      c:endpoint-get-graph
```

**Интеграция с MCP**:
- Расширить `graph_traverse_down(project="fedoc", include_metadata=true)`
- AI получает схему классов при каждом запуске
- Новые MCP команды:
  - `class_create()` — создать класс в графе
  - `class_add_property()` — добавить свойство
  - `class_add_method()` — добавить метод
  - `class_regenerate_code()` — сгенерировать код из графа

**Генератор**:
- `tools/generate_from_graph.py` — читает граф, генерирует классы
- Шаблоны Jinja2 для Python и JavaScript

**Преимущества**:
✅ Граф — единственный источник истины  
✅ AI всегда актуален  
✅ Нет дублирования (YAML, JSON)  
✅ Версионирование изменений классов  
✅ Визуализация структуры в Graph Viewer  
✅ Философия fedoc: всё в графе

---

## Обновлённые файлы

### Исправления в текущем чате

1. **`src/lib/graph_viewer/frontend/src/utils/exportToSVG.js`**
   - Исправлен рендеринг текста (двойной слой)
   - Улучшен расчёт кривых Безье
   - Исправлено чтение конфига кривизны

### Файлы для будущих изменений

**Будут изменены при реализации предложений**:

1. `src/lib/graph_viewer/frontend/src/components/GraphCanvas.vue`
   - Убрать хардкод опций vis-network
   - Делегировать в VisualizationManager

2. `src/lib/graph_viewer/frontend/src/stores/graph.js`
   - Упростить `applyTheme()`
   - Использовать классы для визуализации

3. `src/lib/graph_viewer/frontend/src/config/visualization.json`
   - Станет единственным источником стилей
   - Или будет заменён данными из графа

4. `src/mcp_server/handlers/graph_traverse_down.py`
   - Добавить параметр `include_metadata`
   - Реализовать обход метаузлов

5. `.cursorrules`
   - Обновить инструкцию: `graph_traverse_down(project="fedoc", include_metadata=true)`

---

## План реализации

### Этап 1: Подготовка графа (1-2 дня)
- [ ] Создать узлы `c:meta`, `c:class-system` в графе
- [ ] Добавить базовые определения классов (GraphObject, GraphVertex, GraphEdge)
- [ ] Добавить определения бизнес-классов (Project, Backend)
- [ ] Расширить `graph_traverse_down` для включения метаданных

### Этап 2: Генератор из графа (2-3 дня)
- [ ] Реализовать `GraphSchemaReader` (читает классы из графа)
- [ ] Создать шаблоны Jinja2:
  - [ ] `tools/templates/python_class.jinja2`
  - [ ] `tools/templates/js_class.jinja2`
- [ ] Реализовать `CodeGenerator`
- [ ] Протестировать генерацию базовых классов

### Этап 3: MCP команды (1-2 дня)
- [ ] Реализовать `class_create()`
- [ ] Реализовать `class_add_property()`
- [ ] Реализовать `class_add_method()`
- [ ] Реализовать `class_add_relation()`
- [ ] Интегрировать `class_regenerate_code()`
- [ ] Протестировать полный цикл изменений через MCP

### Этап 4: Миграция существующих классов (2-3 дня)
- [ ] Перенести существующие классы в граф как метаузлы
- [ ] Сгенерировать код из графа
- [ ] Проверить работоспособность фронтенда и бакенда
- [ ] Удалить старые YAML/JSON конфигурации (если применимо)

### Этап 5: Рефакторинг визуализации (2-3 дня)
- [ ] Создать структуру `models/`, `services/`, `renderers/`
- [ ] Реализовать базовые классы на фронтенде
- [ ] Реализовать `VisualizationManager`
- [ ] Убрать хардкод из `GraphCanvas.vue` и `stores/graph.js`
- [ ] Обновить SVG экспорт через классы

### Этап 6: Тестирование (2 дня)
- [ ] Проверить работу AI ассистента с метаданными
- [ ] Проверить синхронизацию фронт-бэк
- [ ] Проверить визуализацию классов в Graph Viewer
- [ ] Проверить canvas и SVG экспорт на консистентность
- [ ] Обновить документацию

**Итого**: 10-15 дней

---

## Следующие шаги

### Для продолжения работы в следующем чате:

1. **Начать с Этапа 1**: Подготовка графа
   - Создать метаузлы в графе
   - Расширить `graph_traverse_down`

2. **Прочитать детальные документы**:
   - [`metadata-in-graph-architecture.md`](./metadata-in-graph-architecture.md) — основная архитектура
   - [`graph-object-class-hierarchy.md`](./graph-object-class-hierarchy.md) — иерархия классов
   - [`frontend-backend-class-sync.md`](./frontend-backend-class-sync.md) — синхронизация

3. **Ключевые вопросы для обсуждения**:
   - Какие базовые классы добавить первыми?
   - Как лучше организовать метаузлы в графе?
   - Нужно ли сразу мигрировать все существующие классы?

---

## Контекст проекта

**Проект**: fedoc (Централизованная система правил и документации)  
**Цель**: Хранить всю информацию о проекте в графе, на клиенте только секреты  
**Технологии**: Python 3.12, PostgreSQL 16 + Apache AGE, Vue.js 3, vis-network

**Философия**: Граф — единственный источник истины.

---

## Ссылки

### Документы
- [Детальная архитектура метаданных в графе](./metadata-in-graph-architecture.md)
- [Иерархия классов GraphObject](./graph-object-class-hierarchy.md)
- [Синхронизация фронтенд-бакенд](./frontend-backend-class-sync.md)

### Изменённые файлы
- `src/lib/graph_viewer/frontend/src/utils/exportToSVG.js`

### Файлы для изменения
- `src/lib/graph_viewer/frontend/src/components/GraphCanvas.vue`
- `src/lib/graph_viewer/frontend/src/stores/graph.js`
- `src/mcp_server/handlers/graph_traverse_down.py`
- `.cursorrules`

### Инструменты для создания
- `tools/generate_from_graph.py`
- `tools/templates/python_class.jinja2`
- `tools/templates/js_class.jinja2`
- `tools/sync_check.py`

---

**Статус**: Готово к реализации  
**Приоритет**: Высокий (решает проблему консистентности и масштабируемости)

