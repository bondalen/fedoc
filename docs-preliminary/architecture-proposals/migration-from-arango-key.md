# Миграция от arango_key к key

**Дата**: 2025-11-05  
**Статус**: Предложение  
**Приоритет**: Средний

---

## Проблема

Поле `arango_key` связано с ArangoDB, но теперь используется PostgreSQL AGE. Название устарело и вводит в заблуждение.

---

## Предложение

Переименовать `arango_key` в `key` (или `node_key` в контексте узлов).

---

## Текущее использование

### В базе данных (PostgreSQL AGE)
```sql
MATCH (n {arango_key: 'c:project'})
RETURN n.arango_key, n.name
```

### В коде Python
```python
node_key = node.get('arango_key')
query = f"MATCH (n {{arango_key: '{key}'}})"
```

### В API
```python
{
    "node_key": "c:project",
    "node_name": "Проект"
}
```

### Во фронтенде
```javascript
const key = node._key || node.arango_key || node.key
```

---

## Предлагаемые изменения

### 1. Переименование в базе данных

**Старое поле**: `arango_key`  
**Новое поле**: `key`

**SQL миграция**:
```sql
-- Миграция существующих данных
ALTER TABLE ag_catalog.vertices 
  ADD COLUMN IF NOT EXISTS key TEXT;

-- Копировать данные
UPDATE ag_catalog.vertices 
SET key = arango_key 
WHERE arango_key IS NOT NULL;

-- Создать индекс
CREATE INDEX IF NOT EXISTS idx_vertices_key ON ag_catalog.vertices(key);

-- Удалить старое поле (после проверки)
-- ALTER TABLE ag_catalog.vertices DROP COLUMN arango_key;
```

**Cypher запросы**:
```cypher
-- Старый формат
MATCH (n {arango_key: 'c:project'})

-- Новый формат
MATCH (n {key: 'a.c.project'})
```

### 2. Обновление кода Python

**Старый код**:
```python
def create_node_in_db(node_key: str, node_name: str, node_type: str, properties: dict):
    query = f"""
        CREATE (n:canonical_node {{
            arango_key: '{node_key}',
            name: '{node_name}',
            node_type: '{node_type}'
        }})
        RETURN id(n)
    """
```

**Новый код**:
```python
def create_node_in_db(node_key: str, node_name: str, properties: dict):
    query = f"""
        CREATE (n:canonical_node {{
            key: '{node_key}',
            name: '{node_name}'
        }})
        RETURN id(n)
    """
    # node_type больше не нужен - извлекается из key
```

### 3. Обновление API

**Старый формат**:
```python
@app.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    node_key = data.get('node_key')
    node_name = data.get('node_name')
    node_type = data.get('node_type')  # ← больше не нужен
```

**Новый формат**:
```python
@app.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    node_key = data.get('key')  # или 'node_key' для совместимости
    node_name = data.get('name')  # или 'node_name'
    # node_type извлекается из key автоматически
```

### 4. Обновление фронтенда

**Старый код**:
```javascript
const key = node._key || node.arango_key || node.key
const type = node.node_type || inferTypeFromKey(key)
```

**Новый код**:
```javascript
const key = node.key || node._key  // приоритет новому полю
const type = extractTypeFromKey(key)  // всегда из ключа
```

---

## План миграции

### Этап 1: Добавить новое поле (без удаления старого)

```sql
-- Добавить новое поле
ALTER TABLE ag_catalog.vertices 
  ADD COLUMN IF NOT EXISTS key TEXT;

-- Копировать данные из старого поля
UPDATE ag_catalog.vertices 
SET key = arango_key 
WHERE arango_key IS NOT NULL AND key IS NULL;

-- Мигрировать ключи в новый формат (если нужно)
UPDATE ag_catalog.vertices 
SET key = migrate_key_format(arango_key, node_type)
WHERE key IS NULL;
```

### Этап 2: Обновить код для работы с обоими полями

```python
def get_node_key(node):
    """Получить ключ узла (поддержка обоих форматов)"""
    return node.get('key') or node.get('arango_key') or node.get('_key')

def find_node_by_key(key: str):
    """Найти узел по ключу (поддержка обоих полей)"""
    query = f"""
        MATCH (n)
        WHERE n.key = '{key}' OR n.arango_key = '{key}'
        RETURN n
    """
```

### Этап 3: Обновить все запросы на новое поле

```python
# Старый
MATCH (n {arango_key: '{key}'})

# Новый
MATCH (n {key: '{key}'})
```

### Этап 4: Удалить старое поле (после проверки)

```sql
-- После проверки, что всё работает
ALTER TABLE ag_catalog.vertices DROP COLUMN arango_key;
```

---

## Структура узла после миграции

### Старая структура
```json
{
  "id": 12345,
  "arango_key": "c:project",
  "name": "Проект",
  "node_type": "concept",
  "properties": {...}
}
```

### Новая структура
```json
{
  "id": 12345,
  "key": "a.c.project",
  "name": "Проект",
  "properties": {...}
}
```

**Изменения**:
- ✅ `arango_key` → `key`
- ✅ `node_type` удалён (извлекается из `key`)
- ✅ Формат ключа: `a.c.project` вместо `c:project`

---

## Обновление функций

### Функция создания узла

**Старая**:
```python
def create_node_in_db(node_key: str, node_name: str, node_type: str, properties: dict):
    query = f"""
        CREATE (n:canonical_node {{
            arango_key: '{node_key}',
            name: '{node_name}',
            node_type: '{node_type}'
        }})
    """
```

**Новая**:
```python
def create_node_in_db(node_key: str, node_name: str, properties: dict):
    # Валидация формата ключа
    if not validate_key_format(node_key):
        raise ValueError(f"Invalid key format: {node_key}")
    
    query = f"""
        CREATE (n:canonical_node {{
            key: '{node_key}',
            name: '{node_name}'
        }})
    """
    # properties добавляются отдельно
```

### Функция поиска узла

**Старая**:
```python
def find_node_by_key(key: str):
    query = f"""
        MATCH (n {{arango_key: '{key}'}})
        RETURN n
    """
```

**Новая**:
```python
def find_node_by_key(key: str):
    query = f"""
        MATCH (n {{key: '{key}'}})
        RETURN n
    """
    # Поддержка старого формата для обратной совместимости
    if not result:
        query = f"""
            MATCH (n {{arango_key: '{key}'}})
            RETURN n
        """
```

---

## Обновление API endpoints

### GET /api/nodes

**Старый ответ**:
```json
{
  "_id": "12345",
  "_key": "c:project",
  "name": "Проект",
  "node_type": "concept"
}
```

**Новый ответ**:
```json
{
  "id": 12345,
  "key": "a.c.project",
  "name": "Проект"
}
```

### POST /api/nodes

**Старый запрос**:
```json
{
  "node_key": "c:project",
  "node_name": "Проект",
  "node_type": "concept",
  "properties": {}
}
```

**Новый запрос**:
```json
{
  "key": "a.c.project",
  "name": "Проект",
  "properties": {}
}
```

---

## Обновление фронтенда

### Компоненты

**Старый код**:
```javascript
// stores/graph.js
const nodeKey = node._key || node.arango_key
const nodeType = node.node_type || inferType(nodeKey)
```

**Новый код**:
```javascript
// stores/graph.js
const nodeKey = node.key || node._key  // приоритет новому полю
const nodeType = extractTypeFromKey(nodeKey)  // всегда из ключа
```

### Визуализация

**Старый код**:
```javascript
// utils/visualization.js
export function getNodeType(node) {
  const key = node._key || node.arango_key
  if (key?.startsWith('c:')) return 'category'
  if (key?.startsWith('t:')) return 'technology'
  // ...
}
```

**Новый код**:
```javascript
// utils/visualization.js
export function getNodeType(node) {
  const key = node.key || node._key
  if (!key) return 'default'
  
  // Новый формат: a.c.project
  const parts = key.split('.')
  if (parts.length >= 2) {
    return `${parts[0]}.${parts[1]}`  // "a.c"
  }
  
  // Старый формат для обратной совместимости
  if (key.startsWith('c:')) return 'a.c'
  if (key.startsWith('t:')) return 'a.t'
  // ...
  
  return 'o.other'
}
```

---

## Преимущества переименования

✅ **Универсальность**: `key` не привязан к конкретной БД  
✅ **Простота**: Короче и понятнее  
✅ **Современность**: Соответствует текущей архитектуре (PostgreSQL AGE)  
✅ **Самодокументируемость**: Понятно, что это ключ узла  

---

## Обратная совместимость

Для плавной миграции можно поддерживать оба поля:

```python
def get_node_key(node):
    """Получить ключ узла (поддержка обоих форматов)"""
    return (
        node.get('key') or 
        node.get('arango_key') or 
        node.get('_key') or 
        node.get('node_key')
    )

def find_node_by_key(key: str):
    """Найти узел (поиск в обоих полях)"""
    query = f"""
        MATCH (n)
        WHERE n.key = '{key}' 
           OR n.arango_key = '{key}'
        RETURN n
    """
```

---

## Итоговая структура узла

```json
{
  "id": 12345,
  "key": "a.c.project",
  "name": "Проект",
  "properties": {
    "description": "Основной проект",
    "repository_url": "https://github.com/..."
  }
}
```

**Поля**:
- `id` — внутренний ID узла (AGE ID)
- `key` — уникальный ключ узла (новый формат: `a.c.project`)
- `name` — отображаемое имя
- `properties` — дополнительные свойства

**Удалены**:
- ❌ `arango_key` (переименован в `key`)
- ❌ `node_type` (извлекается из `key`)

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

