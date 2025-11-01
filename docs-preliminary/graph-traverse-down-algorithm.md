# Алгоритм graph_traverse_down (sys-001)

**Дата**: 2025-11-01  
**Версия**: 1.0  
**Статус**: Спецификация на основе ручного обхода

---

## Назначение

Обход графа проекта вниз от стартового узла по исходящим рёбрам с фильтром по ключу проекта. Реализация принципа **sys-001**: "Сборка документации через обход графа вниз".

---

## Параметры команды

### MCP команда
```python
mcp_fedoc_graph_traverse_down(
    project: str,                # fedoc | fepro | femsq
    start_node: str = None,      # None = c:project, или arango_key
    format: str = "markdown",    # markdown | json
    audience: str = "human"      # human | ai
) -> str
```

### Описание параметров

- **project** (обязательный): Ключ проекта для фильтрации рёбер
- **start_node** (опциональный): 
  - `None` — автоматический поиск корня (`c:project`)
  - `"c:backend"` — начать обход с конкретного узла
  - Поддержка выбора узла из Graph Viewer (будущее)
- **format**: Формат вывода
  - `"markdown"` — текстовый документ с заголовками
  - `"json"` — структурированный JSON
- **audience**: Целевая аудитория
  - `"human"` — подробный, читаемый формат
  - `"ai"` — компактный, машиночитаемый формат

---

## Алгоритм

### Шаг 1: Извлечение подграфа проекта

```python
def build_subgraph(project_key: str) -> Subgraph:
    """
    Построить подграф проекта, отфильтровав рёбра по ключу проекта
    """
    # SQL запрос к PostgreSQL + Apache AGE
    query = """
        LOAD 'age';
        SET search_path = ag_catalog, public;
        
        SELECT * FROM cypher('common_project_graph', $$
          MATCH (a)-[r]->(b)
          WHERE EXISTS(r.projects) AND $project IN r.projects
          RETURN a, r, b
        $$) as (from_node agtype, edge agtype, to_node agtype);
    """
    
    edges = execute_query(query, project=project_key)
    
    # Построить граф смежности
    adjacency = defaultdict(list)
    nodes = {}
    
    for from_node, edge, to_node in edges:
        from_id = from_node['id']
        to_id = to_node['id']
        
        nodes[from_id] = from_node
        nodes[to_id] = to_node
        
        adjacency[from_id].append({
            'to': to_id,
            'type': edge['type'],
            'projects': edge['projects']
        })
    
    return Subgraph(nodes=nodes, adjacency=adjacency)
```

### Шаг 2: Поиск стартового узла

```python
def find_start_node(subgraph: Subgraph, start_key: str = None) -> str:
    """
    Найти стартовый узел для обхода
    """
    if start_key:
        # Пользователь указал конкретный узел
        for node_id, node in subgraph.nodes.items():
            if node['properties']['arango_key'] == start_key:
                return node_id
        raise ValueError(f"Узел {start_key} не найден в подграфе")
    
    # Автоматический поиск c:project
    for node_id, node in subgraph.nodes.items():
        if node['properties']['arango_key'] == 'c:project':
            return node_id
    
    # Если c:project нет, найти корневой узел (без входящих рёбер)
    nodes_with_parents = set()
    for children in subgraph.adjacency.values():
        for child in children:
            nodes_with_parents.add(child['to'])
    
    root_nodes = [nid for nid in subgraph.nodes if nid not in nodes_with_parents]
    
    if not root_nodes:
        raise ValueError("Не найден корневой узел в подграфе")
    
    return root_nodes[0]
```

### Шаг 3: Обход графа вниз (DFS)

```python
class GraphTraverser:
    def __init__(self, subgraph: Subgraph, numbering_system: str = "01-zz"):
        self.subgraph = subgraph
        self.numbering = Numbering01zz()
        self.visited = {}  # {node_id: path}
    
    def traverse(self, start_node_id: str) -> dict:
        """
        Рекурсивный обход графа вниз с нумерацией
        """
        return self._traverse_recursive(start_node_id, path="01")
    
    def _traverse_recursive(self, node_id: str, path: str, edge_type: str = None) -> dict:
        """
        Рекурсивный обход с обработкой повторных включений
        """
        # Проверка на повторное посещение
        if node_id in self.visited:
            # Повторное включение — только ссылка
            return {
                'ref': self.visited[node_id],
                'node': self.subgraph.nodes[node_id]
            }
        
        # Первое посещение — полное описание
        self.visited[node_id] = path
        node = self.subgraph.nodes[node_id]
        props = node['properties']
        
        result = {
            'path': path,
            'key': props['arango_key'],
            'name': props['name'],
            'type': props.get('kind', props.get('node_type', 'unknown')),
            'edge_type': edge_type,
            'properties': self._extract_properties(props),
            'children': {}
        }
        
        # Обход дочерних узлов
        children = self.subgraph.adjacency.get(node_id, [])
        for i, child_edge in enumerate(children):
            child_id = child_edge['to']
            child_num = i + 1
            child_path = f"{path}.{self.numbering.encode(child_num)}"
            
            result['children'][child_path] = self._traverse_recursive(
                child_id,
                child_path,
                edge_type=child_edge['type']
            )
        
        return result
    
    def _extract_properties(self, props: dict) -> dict:
        """
        Извлечь значимые свойства узла (без технических полей)
        """
        exclude_keys = {'_id', '_key', '_rev', 'id', 'arango_key', 'name', 'kind', 'node_type'}
        return {k: v for k, v in props.items() if k not in exclude_keys and v is not None}
```

### Шаг 4: Система нумерации 01-zz

```python
class Numbering01zz:
    """
    Система нумерации dev-001: 01-99, 0a-9z, a0-z9, aa-zz (1295 позиций)
    """
    
    @staticmethod
    def encode(num: int) -> str:
        """Преобразовать число 1-1295 в код 01-zz"""
        if num < 1 or num > 1295:
            raise ValueError(f"Число {num} вне диапазона 1-1295")
        
        # 01-99: числа 1-99
        if num <= 99:
            return f"{num:02d}"
        
        num -= 99
        
        # 0a-9z: числа 100-459
        if num <= 360:
            first = str((num - 1) // 36)
            second_idx = (num - 1) % 36
            if second_idx < 26:
                second = chr(ord('a') + second_idx)
            else:
                second = chr(ord('0') + second_idx - 26)
            return f"{first}{second}"
        
        num -= 360
        
        # a0-z9: числа 460-819
        if num <= 360:
            first_idx = (num - 1) // 10
            second = str((num - 1) % 10)
            first = chr(ord('a') + first_idx)
            return f"{first}{second}"
        
        num -= 360
        
        # aa-zz: числа 820-1295
        first_idx = (num - 1) // 26
        second_idx = (num - 1) % 26
        first = chr(ord('a') + first_idx)
        second = chr(ord('a') + second_idx)
        return f"{first}{second}"
```

### Шаг 5: Генерация вывода

#### Markdown (для человека)

```python
def generate_markdown(tree: dict, node_details: dict) -> str:
    """
    Генерация Markdown документа из дерева обхода
    """
    output = []
    
    # Заголовок
    output.append("# Обход графа: проект {project} от узла {start}\n")
    output.append("**Метаданные**:")
    output.append(f"- Проект: {project}")
    output.append(f"- Стартовый узел: {start_key} ({start_name})")
    output.append(f"- Дата генерации: {datetime.utcnow().isoformat()} UTC")
    output.append(f"- Метод: sys-001 (обход вниз)\n")
    output.append("---\n")
    
    # Дерево
    output.append("## Дерево зависимостей\n")
    output.extend(generate_node_markdown(tree, level=3))
    
    # Статистика
    output.append("\n---\n")
    output.append("## Статистика обхода\n")
    output.append(f"- Уникальных узлов: {unique_count}")
    output.append(f"- Узлы с множественными родителями: {multi_parent_count}")
    
    return '\n'.join(output)

def generate_node_markdown(node: dict, level: int) -> list:
    """
    Рекурсивная генерация Markdown для узла
    """
    lines = []
    
    # Ссылка на повторное включение
    if 'ref' in node:
        header = '#' * level
        lines.append(f"{header} {node['key']} — {node['name']}")
        lines.append(f"→ **См. раздел {node['ref']}** (полное описание выше)\n")
        return lines
    
    # Полное описание
    header = '#' * level
    lines.append(f"{header} {node['key']} — {node['name']}")
    
    if node.get('edge_type'):
        lines.append(f"**Связь**: {node['edge_type']}")
    
    lines.append(f"**Тип**: {node['type']}")
    
    if 'description' in node['properties']:
        lines.append(f"**Описание**: {node['properties']['description']}")
    
    # Дополнительные свойства
    for key, value in node['properties'].items():
        if key != 'description':
            lines.append(f"**{key.title()}**: {value}")
    
    lines.append("")
    
    # Дочерние узлы
    for child_path, child in sorted(node['children'].items()):
        lines.extend(generate_node_markdown(child, level + 1))
    
    return lines
```

#### JSON (для AI)

```python
def generate_json_ai(tree: dict) -> dict:
    """
    Генерация компактного JSON для AI
    Формат: {path: {k: key, n: name, t: type, e: edge, p: props, c: children}}
    """
    def convert_node(node):
        if 'ref' in node:
            return {"ref": node['ref']}
        
        result = {
            "k": node['key'],
            "n": node['name'],
            "t": node['type']
        }
        
        if node.get('edge_type'):
            result["e"] = node['edge_type']
        
        if node['properties']:
            # Сокращённые ключи для экономии токенов
            props = {}
            if 'description' in node['properties']:
                props['d'] = node['properties']['description']
            # Остальные свойства как есть
            for k, v in node['properties'].items():
                if k != 'description':
                    props[k] = v
            
            if props:
                result["p"] = props
        
        if node['children']:
            result["c"] = {path: convert_node(child) 
                          for path, child in node['children'].items()}
        
        return result
    
    return {
        "meta": {
            "project": project,
            "start": start_key,
            "nodes": unique_count,
            "method": "sys-001",
            "generated": datetime.utcnow().isoformat()
        },
        "tree": {
            tree['path']: convert_node(tree)
        },
        "refs": multi_parent_refs,
        "stats": {
            "unique": unique_count,
            "multi_parent": {k: len(v) for k, v in multi_parent_refs.items()},
            "depth": max_depth,
            "cycles": cycles_count
        }
    }
```

---

## Результаты ручного обхода

### Статистика
- **Проект**: fedoc
- **Стартовый узел**: c:project
- **Уникальных узлов**: 20
- **Рёбер в подграфе**: 23
- **Максимальная глубина**: 10 уровней
- **Узлы с множественными родителями**: 2 (t:rest, c:mcp)

### Размеры документов
- **Markdown (human)**: 4 543 байт
- **JSON (AI, formatted)**: 10 239 байт
- **JSON (AI, compact)**: 3 939 байт (экономия 13.3%)

### Файлы
- `/tmp/fedoc_traverse_down_human.md` — Markdown для человека
- `/tmp/fedoc_traverse_down_ai.json` — JSON для AI (форматированный)
- `/tmp/fedoc_traverse_down_ai_compact.json` — JSON для AI (минифицированный)

---

## Ключевые паттерны

### 1. Обработка повторных включений
- **Первое включение**: Полное описание + все дочерние ветви
- **Повторные включения**: Ссылка на первое + NO дочерних ветвей
- **Реализация**: Словарь `visited = {node_id: path}`

### 2. Нумерация узлов
- **Система**: 01-zz (dev-001)
- **Иерархия**: `01`, `01.01`, `01.01.01`, ...
- **Ёмкость**: 1295 позиций на уровень

### 3. Фильтрация рёбер
- **Критерий**: `project_key IN edge.projects`
- **Результат**: Подграф только с рёбрами проекта

### 4. Извлечение свойств
- **Включаем**: name, description, kind, port, stack, version, status
- **Исключаем**: _id, _key, _rev, id (технические поля AGE/ArangoDB)

---

## Архитектура MCP-команды

### Модульная структура
```
src/lib/graph_traversal/
├── __init__.py
├── subgraph_builder.py      # Построение подграфа проекта
├── traverser.py              # Алгоритм обхода DFS
├── numbering.py              # Система нумерации 01-zz
├── markdown_generator.py     # Генерация Markdown
└── json_generator.py         # Генерация JSON

src/mcp_server/handlers/
└── graph_traverse_down.py    # MCP-обёртка
```

### Зависимости
- `psycopg2` — подключение к PostgreSQL
- `json` — парсинг AGE данных
- Нет внешних зависимостей для генерации документов

---

## Следующие шаги

### Краткосрочные
1. ✅ Ручной обход выполнен
2. ⏳ Реализовать библиотеку `graph_traversal`
3. ⏳ Создать MCP-команду `graph_traverse_down`
4. ⏳ Протестировать на проектах fedoc, fepro, femsq

### Долгосрочные
1. Добавить поддержку выбора узла из Graph Viewer
2. Реализовать `graph_traverse_up` для sys-002
3. Добавить кэширование подграфов
4. Оптимизировать для больших графов (>1000 узлов)

---

**Автор**: Claude Sonnet 4.5 + Александр  
**Дата**: 2025-11-01  
**Версия документа**: 1.0

