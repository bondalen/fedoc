# Архитектура: Сегменты графа для фильтрации и визуализации

**Дата**: 2025-11-05  
**Статус**: Предложение  
**Приоритет**: Средний

---

## Концепция

Группировка узлов графа по **сегментам** (логическим областям) позволяет:
1. **Фильтровать граф** при отображении (показывать только нужные сегменты)
2. **Разное оформление рёбер** в зависимости от сегментов узлов
3. **Логическую группировку** узлов по их назначению
4. **Улучшенную навигацию** в больших графах

---

## Определение сегментов

### 1. ArchitectureSegment (Сегмент архитектуры)

**Узлы**:
- `ConceptVertex` (c:) — концепты проекта
- `TechnologyVertex` (t:) — технологии
- `VersionVertex` (v:) — версии технологий

**Назначение**: Описывает архитектуру проекта, технологический стек, зависимости между технологиями.

**Примеры связей**:
- `c:project` → `t:python` (проект использует Python)
- `t:python` → `v:python@3.12` (Python имеет версию 3.12)
- `c:backend` → `t:flask` (бакенд использует Flask)

### 2. CodeStructureSegment (Сегмент структуры кода)

**Узлы**:
- `ModuleVertex` (m:) — модули проекта
- `ComponentVertex` (comp:) — компоненты проекта

**Назначение**: Описывает структуру кода, модули, компоненты, их зависимости.

**Примеры связей**:
- `m:lib.graph_viewer` → `comp:api_server_age` (модуль содержит компонент)
- `comp:api_server_age` → `comp:edge_validator_age` (компонент зависит от компонента)
- `m:mcp_server` → `m:lib.graph_viewer` (модуль использует модуль)

### 3. FileSystemSegment (Сегмент файловой системы)

**Узлы**:
- `DirectoryVertex` (d:) — директории файловой системы

**Назначение**: Описывает структуру файловой системы проекта.

**Примеры связей**:
- `d:src/lib/graph_viewer` → `d:src/lib/graph_viewer/backend` (директория содержит поддиректорию)
- `m:lib.graph_viewer` → `d:src/lib/graph_viewer` (модуль маппится на директорию)

---

## Преимущества сегментации

### 1. Фильтрация графа

```python
# Фильтр: показать только архитектуру
filter_segments = ['architecture']

# Фильтр: показать архитектуру и структуру кода
filter_segments = ['architecture', 'code_structure']

# Фильтр: показать все сегменты
filter_segments = ['architecture', 'code_structure', 'filesystem']
```

**API endpoint**:
```
GET /api/graph?segments=architecture,code_structure
```

### 2. Разное оформление рёбер

#### Рёбра внутри сегмента

**Architecture → Architecture**:
- Стиль: сплошная линия
- Цвет: синий (#1976D2)
- Толщина: 2px
- Примеры: `c:project` → `t:python`, `t:python` → `v:python@3.12`

**CodeStructure → CodeStructure**:
- Стиль: сплошная линия
- Цвет: зелёный (#388E3C)
- Толщина: 2px
- Примеры: `m:lib.graph_viewer` → `comp:api_server_age`

**FileSystem → FileSystem**:
- Стиль: пунктир
- Цвет: серый (#757575)
- Толщина: 1px
- Примеры: `d:src/lib` → `d:src/lib/graph_viewer`

#### Рёбра между сегментами

**Architecture → CodeStructure**:
- Стиль: стрелка с заливкой
- Цвет: оранжевый (#F57C00)
- Толщина: 3px
- Примеры: `c:backend` → `m:lib.graph_viewer.backend`

**CodeStructure → FileSystem**:
- Стиль: пунктир
- Цвет: фиолетовый (#9B59B6)
- Толщина: 2px
- Примеры: `m:lib.graph_viewer` → `d:src/lib/graph_viewer`

**Architecture → FileSystem**:
- Стиль: пунктир
- Цвет: тёмно-синий (#1565C0)
- Толщина: 2px
- Примеры: `c:project` → `d:src`

### 3. Логическая группировка

Сегменты позволяют логически группировать узлы:
- **Архитектура**: "Что использует проект?"
- **Структура кода**: "Как организован код?"
- **Файловая система**: "Где находятся файлы?"

---

## Реализация в классах

### Базовый класс сегмента

```python
# models/segments/base_segment.py
class BaseSegmentVertex(GraphVertex):
    """Базовый класс для сегментов графа"""
    SEGMENT_NAME = None  # Абстрактный
    
    def get_segment(self) -> str:
        """Получить название сегмента"""
        return self.SEGMENT_NAME
    
    @classmethod
    def is_in_segment(cls, node_key: str) -> bool:
        """Проверить, принадлежит ли узел к сегменту"""
        return node_key.startswith(cls.KEY_PREFIX)
```

### Сегмент архитектуры

```python
# models/segments/architecture_segment.py
class ArchitectureSegmentVertex(BaseSegmentVertex):
    """Сегмент архитектуры проекта"""
    SEGMENT_NAME = 'architecture'
    
    @classmethod
    def get_segment_nodes(cls):
        """Получить все типы узлов сегмента"""
        return ['concept', 'technology', 'version']
```

### Сегмент структуры кода

```python
# models/segments/code_structure_segment.py
class CodeStructureSegmentVertex(BaseSegmentVertex):
    """Сегмент структуры кода"""
    SEGMENT_NAME = 'code_structure'
    
    @classmethod
    def get_segment_nodes(cls):
        """Получить все типы узлов сегмента"""
        return ['module', 'component']
```

### Сегмент файловой системы

```python
# models/segments/filesystem_segment.py
class FileSystemSegmentVertex(BaseSegmentVertex):
    """Сегмент файловой системы"""
    SEGMENT_NAME = 'filesystem'
    
    @classmethod
    def get_segment_nodes(cls):
        """Получить все типы узлов сегмента"""
        return ['directory']
```

### Расширение GraphEdge

```python
# models/edges/graph_edge.py
class GraphEdge(GraphObject):
    """Класс для рёбер графа с поддержкой сегментов"""
    
    def get_segment_from(self) -> str:
        """Получить сегмент исходного узла"""
        from_vertex = self.get_from_vertex()
        return from_vertex.get_segment() if from_vertex else None
    
    def get_segment_to(self) -> str:
        """Получить сегмент целевого узла"""
        to_vertex = self.get_to_vertex()
        return to_vertex.get_segment() if to_vertex else None
    
    def get_edge_style_by_segments(self, theme='light') -> dict:
        """Получить стиль рёбра в зависимости от сегментов"""
        segment_from = self.get_segment_from()
        segment_to = self.get_segment_to()
        
        # Рёбра внутри сегмента
        if segment_from == segment_to:
            return self._get_intra_segment_style(segment_from, theme)
        
        # Рёбра между сегментами
        return self._get_inter_segment_style(segment_from, segment_to, theme)
    
    def _get_intra_segment_style(self, segment: str, theme: str) -> dict:
        """Стиль рёбра внутри сегмента"""
        styles = {
            'architecture': {
                'color': '#1976D2',
                'width': 2,
                'dashes': False
            },
            'code_structure': {
                'color': '#388E3C',
                'width': 2,
                'dashes': False
            },
            'filesystem': {
                'color': '#757575',
                'width': 1,
                'dashes': True
            }
        }
        return styles.get(segment, {})
    
    def _get_inter_segment_style(self, segment_from: str, segment_to: str, theme: str) -> dict:
        """Стиль рёбра между сегментами"""
        # Architecture → CodeStructure
        if segment_from == 'architecture' and segment_to == 'code_structure':
            return {'color': '#F57C00', 'width': 3, 'dashes': False}
        
        # CodeStructure → FileSystem
        if segment_from == 'code_structure' and segment_to == 'filesystem':
            return {'color': '#9B59B6', 'width': 2, 'dashes': True}
        
        # Architecture → FileSystem
        if segment_from == 'architecture' and segment_to == 'filesystem':
            return {'color': '#1565C0', 'width': 2, 'dashes': True}
        
        # Обратные связи
        if segment_from == 'code_structure' and segment_to == 'architecture':
            return {'color': '#F57C00', 'width': 3, 'dashes': True}
        
        if segment_from == 'filesystem' and segment_to == 'code_structure':
            return {'color': '#9B59B6', 'width': 2, 'dashes': True}
        
        if segment_from == 'filesystem' and segment_to == 'architecture':
            return {'color': '#1565C0', 'width': 2, 'dashes': True}
        
        # По умолчанию
        return {'color': '#B0BEC5', 'width': 2, 'dashes': False}
```

---

## API расширения

### Фильтрация по сегментам

```python
@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Построить граф с фильтрацией по сегментам"""
    segments = request.args.get('segments', '').split(',')
    segments = [s.strip() for s in segments if s.strip()]
    
    # Если указаны сегменты, фильтруем узлы
    if segments:
        node_types = []
        for segment in segments:
            if segment == 'architecture':
                node_types.extend(['concept', 'technology', 'version'])
            elif segment == 'code_structure':
                node_types.extend(['module', 'component'])
            elif segment == 'filesystem':
                node_types.extend(['directory'])
        
        # Фильтровать узлы по типам
        # ...
```

### Получение сегмента узла

```python
@app.route('/api/nodes/<int:node_id>/segment', methods=['GET'])
def get_node_segment(node_id):
    """Получить сегмент узла"""
    node = get_node_by_id(node_id)
    vertex = create_vertex_from_node(node)
    return jsonify({'segment': vertex.get_segment()})
```

---

## Визуализация на фронтенде

### Определение сегмента

```javascript
// utils/segments.js
export const getNodeSegment = (nodeKey) => {
  if (!nodeKey) return null;
  
  // Architecture segment
  if (nodeKey.startsWith('c:') || 
      nodeKey.startsWith('t:') || 
      nodeKey.startsWith('v:')) {
    return 'architecture';
  }
  
  // Code structure segment
  if (nodeKey.startsWith('m:') || 
      nodeKey.startsWith('comp:')) {
    return 'code_structure';
  }
  
  // File system segment
  if (nodeKey.startsWith('d:')) {
    return 'filesystem';
  }
  
  return null;
};

export const getEdgeStyleBySegments = (edge, fromNode, toNode, theme = 'light') => {
  const segmentFrom = getNodeSegment(fromNode.key || fromNode._key);
  const segmentTo = getNodeSegment(toNode.key || toNode._key);
  
  // Рёбра внутри сегмента
  if (segmentFrom === segmentTo) {
    return getIntraSegmentStyle(segmentFrom, theme);
  }
  
  // Рёбра между сегментами
  return getInterSegmentStyle(segmentFrom, segmentTo, theme);
};
```

### Фильтрация в UI

```vue
<!-- components/SegmentFilter.vue -->
<template>
  <div class="segment-filter">
    <label>
      <input 
        type="checkbox" 
        v-model="selectedSegments" 
        value="architecture"
      />
      Архитектура
    </label>
    <label>
      <input 
        type="checkbox" 
        v-model="selectedSegments" 
        value="code_structure"
      />
      Структура кода
    </label>
    <label>
      <input 
        type="checkbox" 
        v-model="selectedSegments" 
        value="filesystem"
      />
      Файловая система
    </label>
  </div>
</template>
```

---

## Преимущества подхода

✅ **Фильтрация**: Показывать только нужные сегменты  
✅ **Визуализация**: Разное оформление рёбер по сегментам  
✅ **Навигация**: Упрощённая навигация в больших графах  
✅ **Логика**: Группировка узлов по назначению  
✅ **Расширяемость**: Легко добавить новые сегменты  
✅ **Типобезопасность**: Классы обеспечивают валидацию  

---

## Следующие шаги

1. Реализовать базовые классы сегментов
2. Расширить `GraphEdge` для поддержки сегментов
3. Добавить API endpoints для фильтрации
4. Обновить фронтенд для визуализации сегментов
5. Добавить UI компоненты для фильтрации
6. Обновить конфигурацию визуализации

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0




