# MCP-сервер интерактив
_Exported on 16.10.2025 at 17:50:24 GMT+3 from Cursor (1.7.46)_

---

**User**

# Запрос для нового чата: Интеграция Graph Viewer и Cursor AI

Добрый день!

Продолжаем разработку MCP-сервера fedoc. Проект синхронизирован с GitHub (последний коммит: 158b88b).

## Текущее состояние

**fedoc MCP Server версия 2.0.0** - полностью функциональный с системой конфигурации и профилями машин.

**Работающие команды (7):**
- `open_graph_viewer` - запуск системы визуализации
- `graph_viewer_status` - статус компонентов
- `stop_graph_viewer` - остановка системы
- `check_imports`, `check_stubs` - диагностика
- `test_arango`, `test_ssh` - тестирование

**Graph Viewer запущен и работает:**
- 🌐 http://localhost:5173
- ✅ SSH туннель к ArangoDB активен
- ✅ API сервер (порт 8899) работает
- ✅ Vite dev сервер (порт 5173) работает

**Архитектура:**
- Backend: Vue.js 3 (src/lib/graph_viewer/frontend/)
- API: Python Flask (src/lib/graph_viewer/backend/api_server.py)
- База: ArangoDB через SSH туннель (vuege-server)
- Конфигурация: config/graph_viewer.yaml + профили машин

## Следующая задача

**Цель:** Обеспечить интерактив между действиями пользователя в Graph Viewer (браузер) и AI-ассистентом Cursor AI.

**Сценарий использования:**
1. Пользователь выбирает узел или ребро в Graph Viewer (браузер), требуется также множественный выбор узлов и ребер
2. Информация, при нажатии кнопки например, о узле (узлах) автоматически передается в Cursor AI
3. AI может использовать контекст для помощи в разработке

**Возможные подходы:**
- WebSocket соединение между браузером и MCP-сервером
- Polling API для получения событий от Graph Viewer
- Clipboard API для передачи данных
- MCP Resources для передачи состояния
- LocalStorage + file watching

**Важная документация:**
- Принципы проекта: docs/project/project-docs.json (принцип sys-002: контекстная сборка правил)
- История: docs-preliminary/chats/chat-2025-10-16-config-system-and-machine-profiles.md
- Graph Viewer: src/lib/graph_viewer/README.md

## Вопросы для обсуждения

1. Какой подход к интеграции браузер ↔ Cursor AI лучше использовать?
2. Как передавать события клика по узлам в MCP-сервер?
3. Нужно ли создавать новые MCP команды типа `get_selected_node`?
4. Как реализовать принцип sys-002 (сбор правил по графу от артефакта к корню)?

Пожалуйста:
1. Изучите текущую архитектуру Graph Viewer (frontend и backend)
2. Предложите архитектуру двустороннего интерактива
3. Дайте рекомендации по реализации

Пока ничего не меняйте - сначала обсудим подход.

---

**Cursor**

Добрый день! Отличная задача! Давайте изучу текущую архитектуру и предложу решение для интеграции Graph Viewer с Cursor AI.

Начну с анализа ключевых компонентов:

Теперь изучу Vue.js фронтенд:

Теперь изучу документацию по MCP и историю:

Отлично! Теперь изучу текущий профиль машины:

Отлично! Теперь у меня полное понимание архитектуры. Давайте проанализирую задачу и предложу решение.

---

## 📊 Анализ текущей архитектуры

### Текущий стек:
- **Frontend**: Vue.js 3 + Pinia (store) + vis-network  
- **API Backend**: Flask (Python) на порту 8899
- **Dev Server**: Vite на порту 5173
- **Database**: ArangoDB через SSH туннель
- **MCP Server**: Python с 7 командами

### Текущий флоу взаимодействия:
```
Браузер (Vue.js) 
    ↓ HTTP/fetch
API Server (Flask :8899)
    ↓ ArangoDB Client
ArangoDB (через SSH туннель)
```

### События в браузере:
- `selectNode(nodeId)` - клик по узлу (GraphCanvas.vue:148)
- `selectEdge(edgeId)` - клик по ребру (GraphCanvas.vue:155)  
- Данные сохраняются в Pinia store (`selectedObject`)

---

## 🎯 Задача интеграции

**Требуется**: Передать события выбора узлов/рёбер из браузера в Cursor AI через MCP-сервер

**Сценарий использования:**
1. Пользователь кликает на узел в Graph Viewer
2. Информация о узле автоматически становится доступна в Cursor AI  
3. AI может использовать контекст для помощи (реализация принципа sys-002)

---

## 🏗️ Предложение архитектуры

### Вариант 1: **REST API + Polling** (Рекомендуется ⭐)

**Архитектура:**
```
Браузер (Vue.js)
    ↓ POST /api/selection
API Server (:8899)
    ↓ сохраняет в память/файл
MCP Server
    ↓ GET /api/selection
AI Assistant (Cursor)
```

**Реализация:**

#### 1.1. Расширение API сервера
Добавить endpoints в `api_server.py`:

```python
# Глобальное хранилище выбранных объектов (in-memory)
selection_state = {
    "nodes": [],      # Список выбранных узлов
    "edges": [],      # Список выбранных рёбер
    "timestamp": None,
    "details": {}     # Полные данные об объектах
}

@app.route('/api/selection', methods=['POST'])
def save_selection():
    """Сохранить выбранные узлы/рёбра"""
    data = request.json
    selection_state.update({
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "timestamp": time.time(),
        "details": data.get("details", {})
    })
    return {"status": "ok"}

@app.route('/api/selection', methods=['GET'])
def get_selection():
    """Получить текущую выборку"""
    return selection_state
```

#### 1.2. Обновление Vue.js store
В `graph.js` добавить:

```javascript
// Отправка выборки на сервер
const sendSelectionToServer = async (nodes, edges) => {
  try {
    await fetch(`${API_BASE}/selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nodes,
        edges,
        details: {
          selectedObject: selectedObject.value
        }
      })
    })
  } catch (err) {
    console.error('Ошибка отправки выборки:', err)
  }
}

// Обновить selectNode для множественного выбора
const selectNode = async (nodeId) => {
  // ... существующий код ...
  
  // Отправить на сервер
  const selectedNodes = network.value.getSelectedNodes()
  const selectedEdges = network.value.getSelectedEdges()
  await sendSelectionToServer(selectedNodes, selectedEdges)
}
```

#### 1.3. Новая MCP команда
В `graph_viewer_manager.py`:

```python
def get_selected_nodes() -> Dict[str, any]:
    """
    Получить текущую выборку узлов и рёбер из Graph Viewer
    
    Используется для передачи контекста в AI.
    Реализует принцип sys-002: контекстная сборка правил.
    """
    config = get_or_create_config()
    api_port = config.get('ports.api_server', 8899)
    
    try:
        response = requests.get(f'http://localhost:{api_port}/api/selection')
        selection = response.json()
        
        # Получить детали для каждого выбранного узла
        nodes_details = []
        for node_id in selection.get('nodes', []):
            node_response = requests.get(
                f'http://localhost:{api_port}/api/object_details',
                params={'id': node_id}
            )
            nodes_details.append(node_response.json())
        
        return {
            "status": "success",
            "selection": {
                "nodes": selection.get('nodes', []),
                "edges": selection.get('edges', []),
                "timestamp": selection.get('timestamp'),
                "nodes_details": nodes_details
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения выборки: {str(e)}"
        }
```

**Преимущества:**
- ✅ Простая реализация
- ✅ Не требует WebSocket
- ✅ Работает с существующей архитектурой
- ✅ Надёжность (REST API)
- ✅ Легко тестировать

**Недостатки:**
- ⚠️ Требует явный вызов команды из Cursor AI
- ⚠️ Не real-time (но для данного сценария это норма)

---

### Вариант 2: **File-based + Watching**

**Архитектура:**
```
Браузер (Vue.js)
    ↓ POST /api/selection
API Server
    ↓ записывает в файл
    /tmp/fedoc_selection.json
MCP Server
    ↓ читает файл
AI Assistant
```

**Реализация:**

```python
# В api_server.py
SELECTION_FILE = "/tmp/fedoc_selection.json"

@app.route('/api/selection', methods=['POST'])
def save_selection():
    data = request.json
    with open(SELECTION_FILE, 'w') as f:
        json.dump({
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
            "timestamp": time.time(),
            "details": data.get("details", {})
        }, f, indent=2)
    return {"status": "ok"}

# В graph_viewer_manager.py
def get_selected_nodes() -> Dict[str, any]:
    try:
        with open(SELECTION_FILE, 'r') as f:
            selection = json.load(f)
        return {
            "status": "success",
            "selection": selection
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Нет активной выборки"
        }
```

**Преимущества:**
- ✅ Простейшая реализация
- ✅ Персистентность выборки
- ✅ Можно использовать file watching (inotify)

**Недостатки:**
- ⚠️ Файловые операции (медленнее памяти)
- ⚠️ Требует очистку /tmp

---

### Вариант 3: **MCP Resources** (Перспектива на будущее)

**Архитектура:**
```
MCP Server предоставляет Resource:
  fedoc://graph/selection
  
Cursor AI подписывается на изменения
```

**Реализация через MCP Protocol Resources:**

```python
# В server.py
@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="fedoc://graph/selection",
            name="Graph Selection",
            description="Currently selected nodes and edges",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "fedoc://graph/selection":
        selection = get_current_selection()  # Из памяти или файла
        return json.dumps(selection)
```

**Преимущества:**
- ✅ Нативная интеграция с MCP
- ✅ Автоматическое обновление в Cursor AI
- ✅ Стандартный протокол

**Недостатки:**
- ⚠️ Требует изучения MCP Resources API
- ⚠️ Более сложная реализация

---

## 🎯 Рекомендация: Вариант 1 (REST API + MCP команда)

### Поэтапный план реализации:

#### **Этап 1: Базовая интеграция (1-2 часа)**

1. Расширить `api_server.py`:
   - Добавить in-memory хранилище выборки
   - Добавить POST `/api/selection` endpoint
   - Добавить GET `/api/selection` endpoint

2. Обновить Vue.js frontend:
   - Добавить функцию отправки выборки в store
   - Интегрировать в `selectNode()` и `selectEdge()`

3. Добавить MCP команду:
   - `get_selected_nodes()` - получение текущей выборки
   - Регистрация в `server.py`

#### **Этап 2: Множественный выбор (30 мин)**

1. Обновить Vue.js для поддержки `Ctrl+Click`:
   ```javascript
   // В GraphCanvas.vue - опции vis-network
   interaction: {
     multiselect: true,  // Включить множественный выбор
     selectConnectedEdges: false
   }
   ```

2. Обработка множественного выбора:
   ```javascript
   network.on('select', (params) => {
     const nodes = params.nodes  // Массив ID
     const edges = params.edges  // Массив ID
     store.selectMultiple(nodes, edges)
   })
   ```

#### **Этап 3: Кнопка "Отправить в AI" (30 мин)**

1. Добавить кнопку в `ControlPanel.vue`:
   ```vue
   <button @click="sendToAI" class="btn-send-ai">
     🤖 Отправить в Cursor AI
   </button>
   ```

2. Функция отправки:
   ```javascript
   const sendToAI = async () => {
     const selected = network.value.getSelection()
     await store.sendSelectionToServer(selected.nodes, selected.edges)
     
     // Показать уведомление
     alert('Выборка отправлена! Используйте команду "Получить выбранные узлы" в Cursor AI')
   }
   ```

#### **Этап 4: Реализация принципа sys-002 (1 час)**

Добавить команду `get_rules_for_artifact()`:

```python
def get_rules_for_artifact(node_id: str) -> Dict[str, any]:
    """
    Реализация принципа sys-002: контекстная сборка правил
    
    Обходит граф от артефакта к корню проекта,
    собирая все применимые правила.
    """
    config = get_or_create_config()
    
    # AQL запрос для обхода графа от артефакта к корню
    query = """
    FOR v, e, p IN 1..10 INBOUND @start_node GRAPH @graph
        FILTER @project IN e.projects
        COLLECT path = p
        RETURN {
            nodes: path.vertices,
            edges: path.edges,
            rules: (
                FOR node IN path.vertices
                    FILTER HAS(node, 'rules')
                    RETURN node.rules
            )
        }
    """
    
    # Выполнить через API или напрямую
    # Вернуть собранные правила
```

---

## 💡 Дополнительные идеи

### 1. Clipboard Integration (опционально)
Автоматически копировать ID выбранных узлов в буфер обмена:

```javascript
// В graph.js
const copySelectionToClipboard = async (nodes) => {
  const text = nodes.join('\n')
  await navigator.clipboard.writeText(text)
  console.log('Выборка скопирована в буфер обмена')
}
```

### 2. WebSocket для real-time (будущее)
Если понадобится push-уведомления от браузера к AI:

```python
# api_server.py
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('selection_changed')
def handle_selection(data):
    # Broadcast изменение
    emit('selection_update', data, broadcast=True)
```

### 3. Визуальная индикация "отправлено"
Добавить иконку/бейдж на выбранных узлах:

```javascript
// Обновить стиль узла после отправки
nodesDataSet.update({
  id: nodeId,
  borderWidth: 3,
  color: { border: '#00ff00' }  // Зеленая обводка
})
```

---

## 📋 Следующие шаги

**Хотите, чтобы я:**

1. ✅ **Реализовал Вариант 1** (REST API + MCP команда)?
2. ✅ **Добавил множественный выбор** узлов и рёбер?
3. ✅ **Создал кнопку "Отправить в AI"** в интерфейсе?
4. ✅ **Реализовал принцип sys-002** (сбор правил по графу)?

Или сначала обсудим детали архитектуры?

```plaintext
Браузер (Vue.js) 
    ↓ HTTP/fetch
API Server (Flask :8899)
    ↓ ArangoDB Client
ArangoDB (через SSH туннель)
```

```plaintext
Браузер (Vue.js)
    ↓ POST /api/selection
API Server (:8899)
    ↓ сохраняет в память/файл
MCP Server
    ↓ GET /api/selection
AI Assistant (Cursor)
```

```python
# Глобальное хранилище выбранных объектов (in-memory)
selection_state = {
    "nodes": [],      # Список выбранных узлов
    "edges": [],      # Список выбранных рёбер
    "timestamp": None,
    "details": {}     # Полные данные об объектах
}

@app.route('/api/selection', methods=['POST'])
def save_selection():
    """Сохранить выбранные узлы/рёбра"""
    data = request.json
    selection_state.update({
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "timestamp": time.time(),
        "details": data.get("details", {})
    })
    return {"status": "ok"}

@app.route('/api/selection', methods=['GET'])
def get_selection():
    """Получить текущую выборку"""
    return selection_state
```

```javascript
// Отправка выборки на сервер
const sendSelectionToServer = async (nodes, edges) => {
  try {
    await fetch(`${API_BASE}/selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nodes,
        edges,
        details: {
          selectedObject: selectedObject.value
        }
      })
    })
  } catch (err) {
    console.error('Ошибка отправки выборки:', err)
  }
}

// Обновить selectNode для множественного выбора
const selectNode = async (nodeId) => {
  // ... существующий код ...
  
  // Отправить на сервер
  const selectedNodes = network.value.getSelectedNodes()
  const selectedEdges = network.value.getSelectedEdges()
  await sendSelectionToServer(selectedNodes, selectedEdges)
}
```

```python
def get_selected_nodes() -> Dict[str, any]:
    """
    Получить текущую выборку узлов и рёбер из Graph Viewer
    
    Используется для передачи контекста в AI.
    Реализует принцип sys-002: контекстная сборка правил.
    """
    config = get_or_create_config()
    api_port = config.get('ports.api_server', 8899)
    
    try:
        response = requests.get(f'http://localhost:{api_port}/api/selection')
        selection = response.json()
        
        # Получить детали для каждого выбранного узла
        nodes_details = []
        for node_id in selection.get('nodes', []):
            node_response = requests.get(
                f'http://localhost:{api_port}/api/object_details',
                params={'id': node_id}
            )
            nodes_details.append(node_response.json())
        
        return {
            "status": "success",
            "selection": {
                "nodes": selection.get('nodes', []),
                "edges": selection.get('edges', []),
                "timestamp": selection.get('timestamp'),
                "nodes_details": nodes_details
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения выборки: {str(e)}"
        }
```

```plaintext
Браузер (Vue.js)
    ↓ POST /api/selection
API Server
    ↓ записывает в файл
    /tmp/fedoc_selection.json
MCP Server
    ↓ читает файл
AI Assistant
```

```python
# В api_server.py
SELECTION_FILE = "/tmp/fedoc_selection.json"

@app.route('/api/selection', methods=['POST'])
def save_selection():
    data = request.json
    with open(SELECTION_FILE, 'w') as f:
        json.dump({
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
            "timestamp": time.time(),
            "details": data.get("details", {})
        }, f, indent=2)
    return {"status": "ok"}

# В graph_viewer_manager.py
def get_selected_nodes() -> Dict[str, any]:
    try:
        with open(SELECTION_FILE, 'r') as f:
            selection = json.load(f)
        return {
            "status": "success",
            "selection": selection
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Нет активной выборки"
        }
```

```plaintext
MCP Server предоставляет Resource:
  fedoc://graph/selection
  
Cursor AI подписывается на изменения
```

```python
# В server.py
@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="fedoc://graph/selection",
            name="Graph Selection",
            description="Currently selected nodes and edges",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "fedoc://graph/selection":
        selection = get_current_selection()  # Из памяти или файла
        return json.dumps(selection)
```

```javascript
   // В GraphCanvas.vue - опции vis-network
   interaction: {
     multiselect: true,  // Включить множественный выбор
     selectConnectedEdges: false
   }
```

```javascript
   network.on('select', (params) => {
     const nodes = params.nodes  // Массив ID
     const edges = params.edges  // Массив ID
     store.selectMultiple(nodes, edges)
   })
```

```vue
   <button @click="sendToAI" class="btn-send-ai">
     🤖 Отправить в Cursor AI
   </button>
```

```javascript
   const sendToAI = async () => {
     const selected = network.value.getSelection()
     await store.sendSelectionToServer(selected.nodes, selected.edges)
     
     // Показать уведомление
     alert('Выборка отправлена! Используйте команду "Получить выбранные узлы" в Cursor AI')
   }
```

```python
def get_rules_for_artifact(node_id: str) -> Dict[str, any]:
    """
    Реализация принципа sys-002: контекстная сборка правил
    
    Обходит граф от артефакта к корню проекта,
    собирая все применимые правила.
    """
    config = get_or_create_config()
    
    # AQL запрос для обхода графа от артефакта к корню
    query = """
    FOR v, e, p IN 1..10 INBOUND @start_node GRAPH @graph
        FILTER @project IN e.projects
        COLLECT path = p
        RETURN {
            nodes: path.vertices,
            edges: path.edges,
            rules: (
                FOR node IN path.vertices
                    FILTER HAS(node, 'rules')
                    RETURN node.rules
            )
        }
    """
    
    # Выполнить через API или напрямую
    # Вернуть собранные правила
```

```javascript
// В graph.js
const copySelectionToClipboard = async (nodes) => {
  const text = nodes.join('\n')
  await navigator.clipboard.writeText(text)
  console.log('Выборка скопирована в буфер обмена')
}
```

```python
# api_server.py
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('selection_changed')
def handle_selection(data):
    # Broadcast изменение
    emit('selection_update', data, broadcast=True)
```

```javascript
// Обновить стиль узла после отправки
nodesDataSet.update({
  id: nodeId,
  borderWidth: 3,
  color: { border: '#00ff00' }  // Зеленая обводка
})
```

---

**User**

Если упростить задачу. Действия пользователя:
1. Выбрать объект или несколько в браузере. 
2. Нажать кнопку отправить в Cursor AI в браузере. 
3. Увидеть идентификаторы выбранных объектов в чате. 
4. Написать что с ними сделать.
Этого будет достаточно на текущий момент. Уточните предложения.

---

**Cursor**

Отлично! Упрощенная версия гораздо практичнее для начала. Давайте уточним детали:

---

## 🎯 Упрощенный сценарий

### Действия пользователя:
1. **Выбрать объекты** в Graph Viewer (Ctrl+Click для множественного выбора)
2. **Нажать кнопку** "📤 Отправить в Cursor AI"
3. **В Cursor AI** вызвать команду (или автоматически) → увидеть список ID
4. **Написать инструкцию** AI что делать с этими объектами

---

## 🤔 Вопросы для уточнения

### 1. Как идентификаторы попадут в чат?

**Вариант A: Ручной вызов команды** ⭐ (Проще)
```
Пользователь в Cursor AI:
"Покажи выбранные узлы из Graph Viewer"

AI вызывает: get_selected_nodes()

Ответ:
✅ Выбрано 3 узла:
- canonical_nodes/c:backend
- canonical_nodes/t:java@21  
- canonical_nodes/c:api

Что с ними делать?
```

**Вариант B: Автоматическое появление** (Сложнее)
- После нажатия кнопки в браузере → автоматически создается сообщение в чате Cursor
- Требует интеграцию с Cursor API (если доступна)

**Мой вопрос:** Вариант A подходит? Или нужно автоматическое появление в чате?

---

### 2. Что показывать кроме ID?

**Вариант A: Только идентификаторы** (Минимум)
```
canonical_nodes/c:backend
canonical_nodes/t:java@21
```

**Вариант B: ID + краткое описание** ⭐ (Рекомендую)
```
1. canonical_nodes/c:backend
   Тип: concept
   Название: Backend

2. canonical_nodes/t:java@21
   Тип: technology
   Название: Java 21
```

**Вариант C: ID + полные детали** (Много текста)
```
1. canonical_nodes/c:backend
   {
     "_id": "canonical_nodes/c:backend",
     "_key": "c:backend",
     "kind": "concept",
     "name": "Backend",
     "description": "...",
     ...
   }
```

**Мой вопрос:** Какой уровень детализации нужен? Предлагаю вариант B.

---

### 3. Где хранить выборку между кликом и вызовом команды?

**Вариант A: В памяти API сервера** ⭐ (Рекомендую)
- Браузер → POST `/api/selection` → сохранение в глобальную переменную Python
- MCP команда → GET запрос → получение данных
- Преимущества: просто, быстро
- Недостатки: теряется при перезапуске API сервера

**Вариант B: В файле** `/tmp/fedoc_selection.json`
- Браузер → POST `/api/selection` → запись в файл
- MCP команда → чтение файла
- Преимущества: сохраняется при перезапуске
- Недостатки: файловые операции

**Мой вопрос:** Вариант A достаточно? (Если API сервер работает, выборка в памяти)

---

### 4. Название и расположение кнопки?

**Расположение:**
- **Вариант A:** В панели управления сверху (рядом с "Обновить", "Подогнать")
- **Вариант B:** В панели деталей справа (когда объект выбран)
- **Вариант C:** Плавающая кнопка в углу экрана

**Название:**
- "📤 Отправить в Cursor AI"
- "🤖 Передать в AI"
- "📋 Скопировать выборку"

**Мой вопрос:** Куда поместить кнопку? Предлагаю вариант A (панель управления).

---

### 5. Множественный выбор - как?

**Способ выбора:**
- **Ctrl+Click** - добавить к выборке
- **Shift+Click** - выбрать диапазон (для узлов сложно в графе)
- **Рамка мышью** - выделить область (есть в vis-network)

**Визуальная индикация:**
- Выделенные узлы/рёбра подсвечиваются (уже работает в vis-network)
- Показать счётчик: "Выбрано: 3 узла, 1 ребро"

**Мой вопрос:** Ctrl+Click достаточно? Или нужна рамка выделения?

---

## 📋 Моё предложение (уточненное)

### Реализация:

#### 1. **Backend** (api_server.py)
```python
# Глобальное хранилище (in-memory)
selection_state = {
    "nodes": [],
    "edges": [],
    "timestamp": None
}

@app.route('/api/selection', methods=['POST'])
def save_selection():
    data = request.json
    selection_state.update({
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "timestamp": time.time()
    })
    return {"status": "ok", "count": len(selection_state["nodes"])}

@app.route('/api/selection', methods=['GET'])
def get_selection():
    return selection_state
```

#### 2. **Frontend** (Vue.js)

Добавить кнопку в `ControlPanel.vue`:
```vue
<button @click="sendToAI" class="btn-send-ai">
  📤 Отправить в Cursor AI ({{ selectionCount }})
</button>
```

Функция отправки в `graph.js`:
```javascript
const sendSelectionToAI = async () => {
  const nodes = network.value.getSelectedNodes()
  const edges = network.value.getSelectedEdges()
  
  const response = await fetch(`${API_BASE}/selection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nodes, edges })
  })
  
  // Уведомление
  alert(`✅ Отправлено: ${nodes.length} узлов, ${edges.length} рёбер
  
Теперь в Cursor AI используйте команду:
"Покажи выбранные узлы из Graph Viewer"`)
}
```

#### 3. **MCP команда** (graph_viewer_manager.py)

```python
def get_selected_nodes() -> Dict[str, any]:
    """
    Получить объекты, выбранные в Graph Viewer
    
    Использование в Cursor AI:
        "Покажи выбранные узлы"
        "Что выбрано в Graph Viewer?"
    """
    config = get_or_create_config()
    api_port = config.get('ports.api_server', 8899)
    
    try:
        # Получить ID выбранных объектов
        response = requests.get(f'http://localhost:{api_port}/api/selection')
        selection = response.json()
        
        nodes = selection.get('nodes', [])
        edges = selection.get('edges', [])
        
        if not nodes and not edges:
            return {
                "status": "empty",
                "message": "Нет выбранных объектов. Выберите узлы в Graph Viewer и нажмите 'Отправить в Cursor AI'"
            }
        
        # Получить детали для каждого узла
        nodes_details = []
        for node_id in nodes:
            try:
                detail_response = requests.get(
                    f'http://localhost:{api_port}/api/object_details',
                    params={'id': node_id}
                )
                nodes_details.append(detail_response.json())
            except:
                nodes_details.append({"_id": node_id, "error": "Не удалось загрузить"})
        
        # Аналогично для рёбер
        edges_details = []
        for edge_id in edges:
            try:
                detail_response = requests.get(
                    f'http://localhost:{api_port}/api/object_details',
                    params={'id': edge_id}
                )
                edges_details.append(detail_response.json())
            except:
                edges_details.append({"_id": edge_id, "error": "Не удалось загрузить"})
        
        # Форматированный вывод
        result = f"✅ Выбрано в Graph Viewer:\n\n"
        
        if nodes:
            result += f"📦 Узлы ({len(nodes)}):\n"
            for i, node in enumerate(nodes_details, 1):
                result += f"{i}. {node.get('_id', 'N/A')}\n"
                result += f"   Название: {node.get('name', 'N/A')}\n"
                result += f"   Тип: {node.get('kind', 'N/A')}\n"
                if node.get('description'):
                    result += f"   Описание: {node['description'][:100]}...\n"
                result += "\n"
        
        if edges:
            result += f"\n🔗 Рёбра ({len(edges)}):\n"
            for i, edge in enumerate(edges_details, 1):
                result += f"{i}. {edge.get('_id', 'N/A')}\n"
                result += f"   Проекты: {', '.join(edge.get('projects', []))}\n\n"
        
        return {
            "status": "success",
            "message": result,
            "data": {
                "nodes": nodes_details,
                "edges": edges_details
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения выборки: {str(e)}"
        }
```

---

## ✅ Итоговый флоу

```
1. Пользователь в браузере:
   - Ctrl+Click на узлах → выбрано 3 узла
   - Клик "📤 Отправить в Cursor AI"
   - Видит alert: "✅ Отправлено: 3 узлов"

2. Пользователь в Cursor AI:
   - Пишет: "Покажи выбранные узлы из Graph Viewer"
   
3. AI вызывает: get_selected_nodes()

4. AI показывает:
   ✅ Выбрано в Graph Viewer:

   📦 Узлы (3):
   1. canonical_nodes/c:backend
      Название: Backend
      Тип: concept

   2. canonical_nodes/t:java@21
      Название: Java 21
      Тип: technology
   
   3. canonical_nodes/c:api
      Название: API
      Тип: concept

5. Пользователь:
   "Создай документацию для этих компонентов"
   
6. AI использует контекст и помогает
```

---

## ❓ Ваши ответы нужны:

1. **Способ появления в чате:** Вариант A (ручной вызов команды) или автоматически?
2. **Уровень детализации:** Вариант B (ID + краткое описание)?
3. **Хранилище:** Вариант A (память API сервера)?
4. **Расположение кнопки:** В панели управления сверху?
5. **Множественный выбор:** Ctrl+Click достаточно?

После ваших ответов сразу начну реализацию! 🚀

```plaintext
Пользователь в Cursor AI:
"Покажи выбранные узлы из Graph Viewer"

AI вызывает: get_selected_nodes()

Ответ:
✅ Выбрано 3 узла:
- canonical_nodes/c:backend
- canonical_nodes/t:java@21  
- canonical_nodes/c:api

Что с ними делать?
```

```plaintext
canonical_nodes/c:backend
canonical_nodes/t:java@21
```

```plaintext
1. canonical_nodes/c:backend
   Тип: concept
   Название: Backend

2. canonical_nodes/t:java@21
   Тип: technology
   Название: Java 21
```

```plaintext
1. canonical_nodes/c:backend
   {
     "_id": "canonical_nodes/c:backend",
     "_key": "c:backend",
     "kind": "concept",
     "name": "Backend",
     "description": "...",
     ...
   }
```

```python
# Глобальное хранилище (in-memory)
selection_state = {
    "nodes": [],
    "edges": [],
    "timestamp": None
}

@app.route('/api/selection', methods=['POST'])
def save_selection():
    data = request.json
    selection_state.update({
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "timestamp": time.time()
    })
    return {"status": "ok", "count": len(selection_state["nodes"])}

@app.route('/api/selection', methods=['GET'])
def get_selection():
    return selection_state
```

```vue
<button @click="sendToAI" class="btn-send-ai">
  📤 Отправить в Cursor AI ({{ selectionCount }})
</button>
```

```javascript
const sendSelectionToAI = async () => {
  const nodes = network.value.getSelectedNodes()
  const edges = network.value.getSelectedEdges()
  
  const response = await fetch(`${API_BASE}/selection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nodes, edges })
  })
  
  // Уведомление
  alert(`✅ Отправлено: ${nodes.length} узлов, ${edges.length} рёбер
  
Теперь в Cursor AI используйте команду:
"Покажи выбранные узлы из Graph Viewer"`)
}
```

```python
def get_selected_nodes() -> Dict[str, any]:
    """
    Получить объекты, выбранные в Graph Viewer
    
    Использование в Cursor AI:
        "Покажи выбранные узлы"
        "Что выбрано в Graph Viewer?"
    """
    config = get_or_create_config()
    api_port = config.get('ports.api_server', 8899)
    
    try:
        # Получить ID выбранных объектов
        response = requests.get(f'http://localhost:{api_port}/api/selection')
        selection = response.json()
        
        nodes = selection.get('nodes', [])
        edges = selection.get('edges', [])
        
        if not nodes and not edges:
            return {
                "status": "empty",
                "message": "Нет выбранных объектов. Выберите узлы в Graph Viewer и нажмите 'Отправить в Cursor AI'"
            }
        
        # Получить детали для каждого узла
        nodes_details = []
        for node_id in nodes:
            try:
                detail_response = requests.get(
                    f'http://localhost:{api_port}/api/object_details',
                    params={'id': node_id}
                )
                nodes_details.append(detail_response.json())
            except:
                nodes_details.append({"_id": node_id, "error": "Не удалось загрузить"})
        
        # Аналогично для рёбер
        edges_details = []
        for edge_id in edges:
            try:
                detail_response = requests.get(
                    f'http://localhost:{api_port}/api/object_details',
                    params={'id': edge_id}
                )
                edges_details.append(detail_response.json())
            except:
                edges_details.append({"_id": edge_id, "error": "Не удалось загрузить"})
        
        # Форматированный вывод
        result = f"✅ Выбрано в Graph Viewer:\n\n"
        
        if nodes:
            result += f"📦 Узлы ({len(nodes)}):\n"
            for i, node in enumerate(nodes_details, 1):
                result += f"{i}. {node.get('_id', 'N/A')}\n"
                result += f"   Название: {node.get('name', 'N/A')}\n"
                result += f"   Тип: {node.get('kind', 'N/A')}\n"
                if node.get('description'):
                    result += f"   Описание: {node['description'][:100]}...\n"
                result += "\n"
        
        if edges:
            result += f"\n🔗 Рёбра ({len(edges)}):\n"
            for i, edge in enumerate(edges_details, 1):
                result += f"{i}. {edge.get('_id', 'N/A')}\n"
                result += f"   Проекты: {', '.join(edge.get('projects', []))}\n\n"
        
        return {
            "status": "success",
            "message": result,
            "data": {
                "nodes": nodes_details,
                "edges": edges_details
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения выборки: {str(e)}"
        }
```

```plaintext
1. Пользователь в браузере:
   - Ctrl+Click на узлах → выбрано 3 узла
   - Клик "📤 Отправить в Cursor AI"
   - Видит alert: "✅ Отправлено: 3 узлов"

2. Пользователь в Cursor AI:
   - Пишет: "Покажи выбранные узлы из Graph Viewer"
   
3. AI вызывает: get_selected_nodes()

4. AI показывает:
   ✅ Выбрано в Graph Viewer:

   📦 Узлы (3):
   1. canonical_nodes/c:backend
      Название: Backend
      Тип: concept

   2. canonical_nodes/t:java@21
      Название: Java 21
      Тип: technology
   
   3. canonical_nodes/c:api
      Название: API
      Тип: concept

5. Пользователь:
   "Создай документацию для этих компонентов"
   
6. AI использует контекст и помогает
```

---

**User**

Попробую ещё упростить. В самом низу, ниже "панели полного текста" сделать "строку состояния" по всей ширине браузера. При выделении объектов по Cntr+Click туда добавляются что то вроде {id:"_id", desc:"_deskription"}, {...} для каждого выделенного объекта. При снятии выделения соответствующий объект удаляется из этой строки. Пользователь заполняет строку тем, что хочет направить в Cursor AI. Затем в чате пишет "Покажи выбранные объекты из Graph Viewer". MCP-сервер забирает содержимое строки и отображает в чате. Пользователь в чате пишет что нужно с этими объектами делать. Уточните предложения.

---

**Cursor**

Отлично! Это действительно проще и элегантнее. Визуальная строка состояния как "корзина" объектов для отправки в AI. Давайте уточним детали:

---

## 🎯 Уточненный сценарий

### Действия пользователя:
1. **Ctrl+Click на узле/ребре** → объект добавляется в строку состояния внизу
2. **Повторный Ctrl+Click** → объект удаляется из строки
3. **В строке накапливаются** выбранные объекты визуально
4. **В Cursor AI:** "Покажи выбранные объекты из Graph Viewer"
5. **MCP показывает** содержимое строки состояния
6. **Пользователь пишет** что делать с объектами

---

## 🤔 Вопросы для уточнения

### 1. Формат отображения объектов в строке состояния?

**Вариант A: Компактные плашки** ⭐ (Рекомендую)
```
┌──────────────────────────────────────────────────────────────┐
│ [c:backend - Backend] [t:java@21 - Java 21] [c:api - API] × │
└──────────────────────────────────────────────────────────────┘
```
- Каждый объект - отдельная плашка с крестиком для удаления
- Цветовая кодировка (синий - concept, зеленый - technology)

**Вариант B: Текстовый список**
```
┌──────────────────────────────────────────────────────────────┐
│ Выбрано: c:backend (Backend), t:java@21 (Java 21), c:api... │
└──────────────────────────────────────────────────────────────┘
```
- Просто текст через запятую

**Вариант C: JSON-формат (как вы описали)**
```
┌──────────────────────────────────────────────────────────────┐
│ {id:"c:backend", desc:"Backend"}, {id:"t:java@21", desc:...}│
└──────────────────────────────────────────────────────────────┘
```

**Мой вопрос:** Вариант A удобнее? Или именно JSON-формат важен?

---

### 2. Где хранить выборку?

**Вариант A: Только в Vue.js store** ⭐ (Проще)
- Выборка хранится в Pinia store (selectedNodes, selectedEdges)
- MCP команда делает GET запрос к API → API читает из Vue state
- Недостаток: при перезагрузке страницы теряется

**Вариант B: Vue store + синхронизация с API**
- При каждом изменении выборки → POST `/api/selection`
- MCP команда → GET `/api/selection`
- Сохраняется при перезагрузке браузера (если API работает)

**Мой вопрос:** Вариант B (с синхронизацией) нужен? Или достаточно A?

---

### 3. Как отображать много объектов?

**Если выбрано 10-20 объектов:**

**Вариант A: Горизонтальный скролл**
```
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] [obj4] [obj5] [obj6] [obj7] >>> скролл │
└──────────────────────────────────────────────────────────────┘
```

**Вариант B: Счетчик + развертывание**
```
┌──────────────────────────────────────────────────────────────┐
│ Выбрано: 15 объектов [развернуть ▼]                          │
└──────────────────────────────────────────────────────────────┘
```
- По клику разворачивается панель со всеми объектами

**Вариант C: Многострочный режим**
```
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] [obj4] [obj5] [obj6]                    │
│ [obj7] [obj8] [obj9] [obj10] [obj11]                         │
└──────────────────────────────────────────────────────────────┘
```

**Мой вопрос:** Предлагаю вариант B (компактно + можно развернуть)?

---

### 4. Взаимодействие со строкой состояния?

**Вариант A: Только через клики в графе** ⭐ (Проще)
- Строка - только индикатор выборки
- Можно удалять объекты кликом на крестик в плашке

**Вариант B: Редактируемая строка**
- Можно вручную добавить/удалить ID
- Можно вставить JSON из буфера

**Мой вопрос:** Вариант A достаточно?

---

### 5. Что показывать в Cursor AI?

**Вариант A: Краткая сводка** ⭐ (Рекомендую)
```
✅ Выбрано в Graph Viewer (3 объекта):

1. canonical_nodes/c:backend
   Название: Backend
   Тип: concept

2. canonical_nodes/t:java@21
   Название: Java 21
   Тип: technology

3. project_edges/12345
   От: c:backend
   К: t:java@21
   Проекты: fepro
```

**Вариант B: Полные данные JSON**
```
✅ Выбрано в Graph Viewer (3 объекта):

{
  "nodes": [
    {
      "_id": "canonical_nodes/c:backend",
      "_key": "c:backend",
      "name": "Backend",
      "kind": "concept",
      "description": "...",
      ...полный документ...
    },
    ...
  ]
}
```

**Вариант C: Только ID (минимум)**
```
✅ Выбрано в Graph Viewer:

canonical_nodes/c:backend
canonical_nodes/t:java@21
project_edges/12345
```

**Мой вопрос:** Вариант A (краткая сводка с основными полями)?

---

### 6. Кнопка "Очистить выборку"?

**Нужна ли кнопка** в строке состояния:
```
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] ... | Выбрано: 3 | [🗑️ Очистить всё]   │
└──────────────────────────────────────────────────────────────┘
```

**Или достаточно:** удалять объекты по одному через Ctrl+Click или крестик?

---

### 7. Синхронизация выборки с графом?

**Поведение:**

**Вариант A: Строгая синхронизация** ⭐
- Что в строке состояния = что выделено на графе
- Клик на плашке в строке → фокус на узле в графе
- Удаление из строки → снятие выделения на графе

**Вариант B: Независимые**
- Можно выбрать объекты, потом снять выделение на графе
- Строка сохраняет накопленную выборку независимо

**Мой вопрос:** Вариант A (синхронизация)?

---

## 📋 Моё предложение (итоговое)

### Визуальный макет:

```
┌─────────────────────────────────────────────────────────────────┐
│ Graph Viewer                                         [Панель]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        [Граф здесь]                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Панель полного текста (при открытии)                            │
├─────────────────────────────────────────────────────────────────┤
│ 📋 Строка выборки для Cursor AI:                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [c:backend × ] [t:java@21 × ] [c:api × ]  │ 3 объекта │🗑️│ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Поведение:

1. **Ctrl+Click на узле** → добавляется плашка `[c:backend ×]`
2. **Клик на ×** в плашке → удаляется из выборки + снимается выделение на графе
3. **Кнопка 🗑️** → очистить всю выборку
4. **Счетчик** показывает количество
5. **Горизонтальный скролл** если много объектов

### Хранение:
- Vue store + POST `/api/selection` при каждом изменении
- MCP команда → GET `/api/selection`

### Формат в Cursor AI:
```
✅ Выбрано в Graph Viewer (3 объекта):

📦 Узлы (2):
1. canonical_nodes/c:backend
   Название: Backend
   Тип: concept

2. canonical_nodes/t:java@21
   Название: Java 21
   Тип: technology

🔗 Рёбра (1):
1. project_edges/12345
   От: Backend → Java 21
   Проекты: fepro
```

---

## ❓ Ваши ответы:

1. **Формат плашек:** Вариант A (компактные плашки с ×)?
2. **Хранение:** Вариант B (Vue + синхронизация с API)?
3. **Много объектов:** Горизонтальный скролл + счетчик?
4. **Редактирование:** Только через клики (не редактируемая строка)?
5. **Вывод в AI:** Вариант A (краткая сводка)?
6. **Кнопка очистки:** Нужна?
7. **Синхронизация:** Строгая (выборка = выделение на графе)?

Подтвердите или скорректируйте, и я сразу начну реализацию! 🚀

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ [c:backend - Backend] [t:java@21 - Java 21] [c:api - API] × │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ Выбрано: c:backend (Backend), t:java@21 (Java 21), c:api... │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ {id:"c:backend", desc:"Backend"}, {id:"t:java@21", desc:...}│
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] [obj4] [obj5] [obj6] [obj7] >>> скролл │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ Выбрано: 15 объектов [развернуть ▼]                          │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] [obj4] [obj5] [obj6]                    │
│ [obj7] [obj8] [obj9] [obj10] [obj11]                         │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
✅ Выбрано в Graph Viewer (3 объекта):

1. canonical_nodes/c:backend
   Название: Backend
   Тип: concept

2. canonical_nodes/t:java@21
   Название: Java 21
   Тип: technology

3. project_edges/12345
   От: c:backend
   К: t:java@21
   Проекты: fepro
```

```plaintext
✅ Выбрано в Graph Viewer (3 объекта):

{
  "nodes": [
    {
      "_id": "canonical_nodes/c:backend",
      "_key": "c:backend",
      "name": "Backend",
      "kind": "concept",
      "description": "...",
      ...полный документ...
    },
    ...
  ]
}
```

```plaintext
✅ Выбрано в Graph Viewer:

canonical_nodes/c:backend
canonical_nodes/t:java@21
project_edges/12345
```

```plaintext
┌──────────────────────────────────────────────────────────────┐
│ [obj1] [obj2] [obj3] ... | Выбрано: 3 | [🗑️ Очистить всё]   │
└──────────────────────────────────────────────────────────────┘
```

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│ Graph Viewer                                         [Панель]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        [Граф здесь]                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Панель полного текста (при открытии)                            │
├─────────────────────────────────────────────────────────────────┤
│ 📋 Строка выборки для Cursor AI:                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [c:backend × ] [t:java@21 × ] [c:api × ]  │ 3 объекта │🗑️│ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

```plaintext
✅ Выбрано в Graph Viewer (3 объекта):

📦 Узлы (2):
1. canonical_nodes/c:backend
   Название: Backend
   Тип: concept

2. canonical_nodes/t:java@21
   Название: Java 21
   Тип: technology

🔗 Рёбра (1):
1. project_edges/12345
   От: Backend → Java 21
   Проекты: fepro
```

---

**User**

1. Компактные плашки без х. Перечень определяется выделением/снятием выделения в графе стандартными методами. 2. Хранение только в Vue. 3. Да. 4. Только через клики. 5. Да. 6. Нет. Снятие выделения - клик на пустом месте графа. 7. Да. Уточните предложения.

---

**Cursor**

Отлично! Всё становится предельно ясно. Давайте финализируем детали:

---

## 🎯 Финальный сценарий

### Действия пользователя:
1. **Ctrl+Click** на узлах/рёбрах в графе → добавляются в выборку
2. **Строка состояния** автоматически обновляется (плашки появляются/исчезают)
3. **Клик на пустом месте** графа → снятие всего выделения → строка очищается
4. **В Cursor AI:** "Покажи выбранные объекты из Graph Viewer"
5. **MCP показывает** краткую сводку
6. **Пользователь:** "Создай документацию для этих компонентов"

---

## 🤔 Финальные уточнения

### 1. Что показывать в плашках?

**Вариант A: ID (_key)** 
```
┌─────────────────────────────────────────────────────┐
│ [c:backend] [t:java@21] [c:api]  │ 3 объекта        │
└─────────────────────────────────────────────────────┘
```

**Вариант B: Название** ⭐ (Рекомендую)
```
┌─────────────────────────────────────────────────────┐
│ [Backend] [Java 21] [API]  │ 3 объекта              │
└─────────────────────────────────────────────────────┘
```

**Вариант C: ID + Название** (может быть длинно)
```
┌─────────────────────────────────────────────────────┐
│ [c:backend - Backend] [t:java@21 - Java 21] ...     │
└─────────────────────────────────────────────────────┘
```

**Мой вопрос:** Что в плашках? Предлагаю B (только название, компактно).

---

### 2. Цветовая кодировка плашек?

**Вариант A: Одинаковые серые плашки**
```
[Backend] [Java 21] [API]
```

**Вариант B: По типу объекта** ⭐ (Рекомендую)
```
[Backend] (синий - concept)
[Java 21] (зеленый - technology)
[Backend → Java 21] (оранжевый - ребро)
```

**Мой вопрос:** Цветовая кодировка нужна?

---

### 3. Интерактивность плашек?

**Вариант A: Статичные** (только индикатор)
- Плашки не кликабельны
- Только визуализация выборки

**Вариант B: Кликабельные** ⭐ (Удобнее)
- Клик на плашке → фокус на соответствующий узел в графе
- Hover → подсветка узла

**Мой вопрос:** Сделать кликабельными для фокусировки?

---

### 4. Передача данных в MCP - как?

**Проблема:** Хранение только в Vue store, но MCP сервер (Python) должен получить данные.

**Вариант A: Vue → POST при каждом изменении** ⭐ (Рекомендую)
```javascript
// При изменении выборки в Vue
watch([selectedNodes, selectedEdges], async (newVal) => {
  // Отправить на API сервер
  await fetch('/api/selection', {
    method: 'POST',
    body: JSON.stringify({ nodes: ..., edges: ... })
  })
})
```
- API сервер хранит в памяти (глобальная переменная)
- MCP команда читает из API сервера
- Технически хранение: Vue (источник) + API (кэш для MCP)

**Вариант B: MCP делает HTTP запрос к Vite dev серверу**
- Сложнее, нужен endpoint в Vue приложении
- Не рекомендую

**Мой вопрос:** Вариант A подходит? (Vue отправляет на API при изменениях)

---

### 5. Что делать с рёбрами?

**Рёбра в графе можно тоже выбирать.** Как показывать в строке?

**Вариант A: Отдельные плашки для рёбер**
```
┌─────────────────────────────────────────────────────┐
│ Узлы: [Backend] [Java 21] │ Рёбра: [Backend→Java21]│
└─────────────────────────────────────────────────────┘
```

**Вариант B: Все вместе с иконками** ⭐ (Проще)
```
┌─────────────────────────────────────────────────────┐
│ [📦Backend] [📦Java 21] [🔗Backend→Java]  │ 3 объекта│
└─────────────────────────────────────────────────────┘
```

**Вариант C: Только узлы в строке**
- Рёбра не показываем
- Фокус на узлах

**Мой вопрос:** Как показывать рёбра? Предлагаю B (иконки).

---

### 6. Высота строки состояния?

**Вариант A: Фиксированная 50-60px** ⭐
- Одна строка плашек
- Скролл если не влезают

**Вариант B: Адаптивная**
- Растёт при большом количестве
- Может занять много места

**Мой вопрос:** Фиксированная высота?

---

## 📋 Моё финальное предложение

### Визуальный дизайн:

```
┌─────────────────────────────────────────────────────────────────┐
│ Graph Viewer                                         [Панель]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        [Граф здесь]                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ 📋 Выбрано для Cursor AI (3 объекта):                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [📦 Backend] [📦 Java 21] [🔗 Backend→Java] [📦 API] >>>    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
   ↑ 50px высота, горизонтальный скролл
```

### Компоненты для реализации:

1. **SelectionBar.vue** (новый компонент)
   - Строка состояния внизу
   - Плашки с цветовой кодировкой
   - Счетчик объектов
   - Горизонтальный скролл

2. **graph.js** (обновить store)
   - Добавить реактивные массивы `selectedNodesList`, `selectedEdgesList`
   - watch для отправки на API при изменениях
   - Синхронизация с vis-network selection events

3. **GraphCanvas.vue** (обновить)
   - Обработчики `select` и `deselect` событий
   - Синхронизация выделения в графе ↔ store

4. **api_server.py** (добавить endpoints)
   ```python
   POST /api/selection  # Сохранить выборку
   GET  /api/selection  # Получить выборку
   ```

5. **graph_viewer_manager.py** (новая команда)
   ```python
   def get_selected_nodes()  # MCP команда
   ```

### Технический флоу:

```
1. Пользователь: Ctrl+Click на узле
   ↓
2. vis-network: событие 'select'
   ↓
3. GraphCanvas.vue: обновляет store.selectedNodesList
   ↓
4. Vue watch: POST /api/selection
   ↓
5. API server: сохраняет в памяти
   ↓
6. SelectionBar.vue: реактивно обновляет плашки

---

7. Пользователь в Cursor AI: "Покажи выбранные объекты"
   ↓
8. MCP команда: GET /api/selection
   ↓
9. API server: возвращает список ID
   ↓
10. MCP: GET /api/object_details для каждого ID
   ↓
11. MCP: форматирует и показывает в чате
```

---

## ❓ Финальные вопросы:

1. **Содержимое плашек:** Вариант B (только название)?
2. **Цвета плашек:** По типу объекта (синий/зеленый/оранжевый)?
3. **Кликабельность:** Клик на плашке → фокус на узле?
4. **Передача в MCP:** Вариант A (Vue → POST → API)?
5. **Рёбра:** Показывать с иконкой 🔗?
6. **Высота строки:** Фиксированная 50-60px?

После подтверждения начну реализацию сразу всех компонентов! 🚀

```plaintext
┌─────────────────────────────────────────────────────┐
│ [c:backend] [t:java@21] [c:api]  │ 3 объекта        │
└─────────────────────────────────────────────────────┘
```

```plaintext
┌─────────────────────────────────────────────────────┐
│ [Backend] [Java 21] [API]  │ 3 объекта              │
└─────────────────────────────────────────────────────┘
```

```plaintext
┌─────────────────────────────────────────────────────┐
│ [c:backend - Backend] [t:java@21 - Java 21] ...     │
└─────────────────────────────────────────────────────┘
```

```plaintext
[Backend] [Java 21] [API]
```

```plaintext
[Backend] (синий - concept)
[Java 21] (зеленый - technology)
[Backend → Java 21] (оранжевый - ребро)
```

```javascript
// При изменении выборки в Vue
watch([selectedNodes, selectedEdges], async (newVal) => {
  // Отправить на API сервер
  await fetch('/api/selection', {
    method: 'POST',
    body: JSON.stringify({ nodes: ..., edges: ... })
  })
})
```

```plaintext
┌─────────────────────────────────────────────────────┐
│ Узлы: [Backend] [Java 21] │ Рёбра: [Backend→Java21]│
└─────────────────────────────────────────────────────┘
```

```plaintext
┌─────────────────────────────────────────────────────┐
│ [📦Backend] [📦Java 21] [🔗Backend→Java]  │ 3 объекта│
└─────────────────────────────────────────────────────┘
```

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│ Graph Viewer                                         [Панель]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        [Граф здесь]                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ 📋 Выбрано для Cursor AI (3 объекта):                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [📦 Backend] [📦 Java 21] [🔗 Backend→Java] [📦 API] >>>    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
   ↑ 50px высота, горизонтальный скролл
```

```python
   POST /api/selection  # Сохранить выборку
   GET  /api/selection  # Получить выборку
```

```python
   def get_selected_nodes()  # MCP команда
```

```plaintext
1. Пользователь: Ctrl+Click на узле
   ↓
2. vis-network: событие 'select'
   ↓
3. GraphCanvas.vue: обновляет store.selectedNodesList
   ↓
4. Vue watch: POST /api/selection
   ↓
5. API server: сохраняет в памяти
   ↓
6. SelectionBar.vue: реактивно обновляет плашки

---

7. Пользователь в Cursor AI: "Покажи выбранные объекты"
   ↓
8. MCP команда: GET /api/selection
   ↓
9. API server: возвращает список ID
   ↓
10. MCP: GET /api/object_details для каждого ID
   ↓
11. MCP: форматирует и показывает в чате
```

