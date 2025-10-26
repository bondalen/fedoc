# Диагностика и исправление системы mcp-fedoc

**Дата:** 26 января 2025  
**Участники:** Александр (пользователь), Claude (ассистент)  
**Тема:** Полная диагностика и исправление команд mcp-fedoc после реализации нормализованной архитектуры проектов

## 🎯 Цели сессии

1. Провести полную диагностику системы mcp-fedoc после изменений в Graph Viewer
2. Исправить проблемы с получением выделенных объектов из браузера
3. Устранить ошибки в команде создания рёбер
4. Исправить фундаментальную проблему с направлением рёбер в PostgreSQL

## 🔍 Выявленные проблемы

### 1. **Ошибка WebSocket соединения**
- **Проблема:** `TypeError: Private element is not present on this object` в `vis-network.js`
- **Причина:** Прямые вызовы `network.value.getSelectedNodes()` и `network.value.getSelectedEdges()`
- **Решение:** Переписана функция `sendSelectionToServer` для использования данных из Pinia store

### 2. **Ошибка "_id" в команде add_edge**
- **Проблема:** `Неожиданная ошибка: '_id'` при создании рёбер
- **Причина:** Неправильная обработка `agtype` значений и извлечение `edge_id` из API ответов
- **Решение:** Исправлена функция `agtype_to_python` и обновлены обработчики в `edge_manager.py` и `server.py`

### 3. **Неправильное направление рёбер**
- **Проблема:** Рёбра отображались в обратном направлении (например, `c:backend-framework` → `v:java@21` вместо `v:java@21` → `c:backend-framework`)
- **Причина:** PostgreSQL функция `get_all_graph_for_viewer` использовала неопределённый Cypher запрос `(n)-[e]-(m)`
- **Решение:** Изменён запрос на направленный `(n)-[e]->(m)` и убраны все костыли из API

## 🛠️ Выполненные исправления

### Frontend (Graph Viewer)
```javascript
// src/lib/graph_viewer/frontend/src/stores/graph.js
const sendSelectionToServer = () => {
  // Используем данные из store вместо прямых вызовов vis-network
  const selectedNodes = (selectedNodesList.value || []).map(n => 
    (n && typeof n === 'object' ? (n.id ?? n) : n)
  )
  const selectedEdges = (selectedEdgesList.value || []).map(e => 
    (e && typeof e === 'object' ? (e.id ?? e) : e)
  )
  // ... остальная логика
}
```

### Backend (API Server)
```python
# src/lib/graph_viewer/backend/api_server_age.py
def agtype_to_python(agtype_value):
    # Улучшенная обработка agtype значений
    if isinstance(parsed, dict) and '_id' in parsed:
        return parsed['_id']
    return parsed
```

### PostgreSQL функция
```sql
-- dev/docker/init-scripts/postgres/06-graph-viewer-functions.sql
MATCH (n:canonical_node)-[e:project_relation]->(m:canonical_node)
-- Изменено с (n)-[e]-(m) на (n)-[e]->(m) для корректного направления
```

## 📊 Результаты тестирования

### ✅ Работающие команды
- `mcp_fedoc_graph_viewer_status` - 100% работает
- `mcp_fedoc_check_imports` - 100% работает  
- `mcp_fedoc_check_stubs` - 100% работает
- `mcp_fedoc_get_selected_nodes` - 100% работает стабильно
- `mcp_fedoc_add_edge` - 100% работает корректно
- `mcp_fedoc_delete_edge` - 100% работает
- `mcp_fedoc_check_edge_uniqueness` - 100% работает

### 🎯 Созданные связи
В ходе тестирования созданы следующие связи:
1. `t:spring-boot` → `c:backend-api` (uses)
2. `t:spring-boot` → `c:backend-reactive` (uses)  
3. `t:spring-boot` → `c:backend-migrations` (uses)
4. `t:spring-boot` → `c:backend-security` (uses)
5. `t:spring-boot` → `c:backend-cache` (uses)
6. `t:spring-boot` → `c:backend-monitoring` (uses)

## 🧹 Очистка

### Удалённые временные файлы
- `update_graph_function.sql` - временный SQL скрипт
- `fix_direction.sql` - временный SQL скрипт
- `/tmp/all_nodes.txt` и `/tmp/connected_nodes.txt` - временные файлы анализа

### Удалённые отладочные компоненты
- Endpoint `/api/debug/raw-graph` - отладочный endpoint
- Endpoint `/api/fix-direction` - временный endpoint для исправления
- Все костыли в API коде для исправления направления рёбер

## 🎉 Итоговый статус

**✅ Система mcp-fedoc полностью функциональна!**

- **Все команды работают корректно** без костылей и временных исправлений
- **Направление рёбер исправлено** на уровне PostgreSQL функции
- **WebSocket соединение стабильно** работает с браузером
- **Создание и удаление рёбер** работает в правильном направлении
- **Получение выделенных объектов** работает надёжно

## 📝 Технические детали

### Архитектура исправлений
1. **PostgreSQL** - исправлена функция `get_all_graph_for_viewer` для корректного направления
2. **API Server** - убраны костыли, используется правильное направление из БД
3. **Frontend** - переписана функция получения выделенных объектов
4. **MCP Server** - исправлена обработка ошибок в командах

### Ключевые файлы
- `src/lib/graph_viewer/frontend/src/stores/graph.js` - исправлена функция `sendSelectionToServer`
- `src/lib/graph_viewer/backend/api_server_age.py` - исправлена функция `agtype_to_python`
- `src/mcp_server/handlers/edge_manager.py` - исправлено извлечение `edge_id`
- `dev/docker/init-scripts/postgres/06-graph-viewer-functions.sql` - исправлен Cypher запрос

**Система готова к продуктивному использованию!** 🚀
