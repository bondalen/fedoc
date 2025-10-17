# Руководство по валидации рёбер графа

**Дата создания:** 17.10.2025  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию

---

## 📋 Обзор

Система валидации рёбер предотвращает создание дублирующих связей в графе проектов. Валидация работает **в обоих направлениях**: если существует связь A→B, то попытка создать A→B или B→A будет отклонена.

### Почему не триггеры ArangoDB?

- **ArangoDB Community Edition не поддерживает триггеры** (только Enterprise)
- **Решение:** Валидация реализована на уровне приложения (Python)
- **Преимущества:** Работает в любой версии ArangoDB, гибкая логика, подробные сообщения об ошибках

---

## 🏗️ Архитектура

### Компоненты

```
┌─────────────────────────────────────────┐
│        Frontend (Graph Viewer)          │
└──────────────┬──────────────────────────┘
               │ HTTP REST API
┌──────────────▼──────────────────────────┐
│         API Server (Flask)               │
│  • POST /api/edges                       │
│  • PUT /api/edges/<id>                   │
│  • DELETE /api/edges/<id>                │
│  • POST /api/edges/check                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Edge Validator (Python)             │
│  • check_edge_uniqueness()               │
│  • insert_edge_safely()                  │
│  • update_edge_safely()                  │
│  • delete_edge()                         │
└──────────────┬──────────────────────────┘
               │ AQL Queries
┌──────────────▼──────────────────────────┐
│          ArangoDB (fedoc)                │
│  • canonical_nodes (вершины)             │
│  • project_relations (рёбра)             │
└──────────────────────────────────────────┘
```

### Файлы

| Файл | Описание |
|------|----------|
| `src/lib/graph_viewer/backend/edge_validator.py` | Модуль валидации рёбер |
| `src/lib/graph_viewer/backend/api_server.py` | REST API endpoints |
| `src/mcp_server/handlers/edge_manager.py` | MCP handler для работы со связями |
| `src/mcp_server/server.py` | MCP команды (add_edge, update_edge, delete_edge, check_edge_uniqueness) |

---

## 🔧 API Reference

### 1. Проверка уникальности

**Endpoint:** `POST /api/edges/check`

**Request:**
```json
{
  "_from": "canonical_nodes/c:backend",
  "_to": "canonical_nodes/t:java@21",
  "exclude_edge_id": "project_relations/12345"  // optional
}
```

**Response (уникальна):**
```json
{
  "is_unique": true,
  "error": null
}
```

**Response (не уникальна):**
```json
{
  "is_unique": false,
  "error": "Связь между узлами 'c:backend' и 't:java@21' уже существует (прямая связь: c:backend → t:java@21, ID: project_relations/85295)"
}
```

---

### 2. Создание ребра

**Endpoint:** `POST /api/edges`

**Request:**
```json
{
  "_from": "canonical_nodes/c:backend",
  "_to": "canonical_nodes/t:java@21",
  "relationType": "uses",
  "projects": ["fepro", "femsq"]
}
```

**Response (успех):**
```json
{
  "success": true,
  "edge": {
    "_id": "project_relations/245476",
    "_key": "245476",
    "_rev": "_kdLvvvS---"
  }
}
```

**Response (дубликат):**
```json
{
  "success": false,
  "error": "Связь между узлами 'c:backend' и 't:java@21' уже существует (прямая связь: c:backend → t:java@21, ID: project_relations/85295)"
}
```

**HTTP коды:**
- `200` - успешно создано
- `409` - конфликт (дубликат)
- `400` - неверный запрос
- `500` - ошибка сервера

---

### 3. Обновление ребра

**Endpoint:** `PUT /api/edges/<path:edge_id>`

**Request:**
```json
{
  "_from": "canonical_nodes/c:backend",  // optional
  "_to": "canonical_nodes/t:java@21",     // optional
  "relationType": "depends_on",           // optional
  "projects": ["fepro"]                    // optional
}
```

**Response:**
```json
{
  "success": true,
  "edge": {
    "_id": "project_relations/245476",
    "_key": "245476",
    "_rev": "_kdLvvvS--A"
  }
}
```

**⚠️ Примечание:** При обновлении `_from` или `_to` также проверяется уникальность новой связи.

**Статус:** ✅ Работает (исправлено 17.10.2025)

---

### 4. Удаление ребра

**Endpoint:** `DELETE /api/edges/<path:edge_id>`

**Response:**
```json
{
  "success": true,
  "message": "Ребро project_relations/245476 успешно удалено"
}
```

**HTTP коды:**
- `200` - успешно удалено
- `404` - ребро не найдено
- `500` - ошибка сервера

---

## 🎯 MCP Команды

### Доступные команды:

| Команда | Описание |
|---------|----------|
| `add_edge` | Добавить ребро с валидацией |
| `update_edge` | Обновить ребро |
| `delete_edge` | Удалить ребро |
| `check_edge_uniqueness` | Проверить уникальность |

### Примеры использования:

#### Проверка уникальности
```python
check_edge_uniqueness(
    from_node="canonical_nodes/c:backend",
    to_node="canonical_nodes/t:java@21"
)
```

#### Добавление ребра
```python
add_edge(
    from_node="canonical_nodes/c:backend",
    to_node="canonical_nodes/t:java@21",
    relation_type="uses",
    projects=["fepro", "femsq"]
)
```

#### Удаление ребра
```python
delete_edge(
    edge_id="project_relations/245476"
)
```

**⚠️ Примечание:** MCP команды требуют перезапуска Cursor/MCP сервера для загрузки обновленного кода.

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Комплексный тест валидации
bash /tmp/test_edge_validation.sh
```

### Результаты тестов (17.10.2025)

| Тест | Результат | Описание |
|------|-----------|----------|
| ✅ Проверка уникальности | PASSED | Корректно определяет существующие связи |
| ✅ Прямой дубликат (A→B + A→B) | PASSED | Отклоняется с правильным сообщением |
| ✅ Обратный дубликат (A→B + B→A) | PASSED | **Отклоняется с указанием "обратная связь"** |
| ✅ Создание уникальной связи | PASSED | Успешно создается |
| ✅ Удаление ребра | PASSED | Успешно удаляется |
| ✅ **Обновление ребра** | **PASSED** | **Работает с валидацией** |

---

## 🔍 Логика валидации

### Алгоритм проверки уникальности

```python
def check_edge_uniqueness(from_node, to_node, exclude_edge_id=None):
    """
    Проверяет существование связи в ОБОИХ направлениях
    
    Запрос AQL:
    FOR e IN project_relations
        FILTER (e._from == @from AND e._to == @to) 
            OR (e._from == @to AND e._to == @from)
        [FILTER e._id != @exclude_id]  // при обновлении
        LIMIT 1
        RETURN e
    """
    # Если найдена хотя бы одна связь - не уникальна
    # Определяется направление: прямая или обратная
    # Возвращается подробное сообщение об ошибке
```

### Примеры

**Случай 1: Прямой дубликат**
```
Существует: A → B (ID: 123)
Попытка:    A → B
Результат:  ❌ "Связь уже существует (прямая связь: A → B, ID: 123)"
```

**Случай 2: Обратный дубликат**
```
Существует: A → B (ID: 123)
Попытка:    B → A
Результат:  ❌ "Связь уже существует (обратная связь: B → A, ID: 123)"
```

**Случай 3: Уникальная связь**
```
Существует: A → B
Попытка:    A → C
Результат:  ✅ Создание разрешено
```

---

## 📊 Статус функций

| Функция | Статус | Примечания |
|---------|--------|------------|
| `check_edge_uniqueness()` | ✅ Работает | Проверка в обоих направлениях |
| `insert_edge_safely()` | ✅ Работает | Автоматическая валидация при вставке |
| `delete_edge()` | ✅ Работает | Удаление по ID |
| `update_edge_safely()` | ✅ Работает | Обновление с валидацией уникальности |

### Известные проблемы

1. ~~⚠️ **UPDATE endpoint**~~ - ✅ **ИСПРАВЛЕНО** (17.10.2025)
   - ~~**Причина:** Неправильная передача параметров в `collection.update()`~~
   - **Решение:** Передача словаря `{'_key': key}` вместо строки
   - **Статус:** Полностью работает

2. ⚠️ **MCP команды** - Требуют перезапуска
   - **Причина:** Cursor кэширует MCP сервер
   - **Workaround:** Перезапустить Cursor
   - **Приоритет:** Низкий

---

## 🚀 Развертывание

### 1. Запуск Graph Viewer с валидацией

```bash
# Через MCP команду
mcp_fedoc_open_graph_viewer()

# Или вручную
cd /home/alex/fedoc
source venv/bin/activate
python3 src/lib/graph_viewer/backend/api_server.py \
    --db-password 'aR@ng0Pr0d2025xK9mN8pL'
```

### 2. Проверка работы

```bash
# Тест API
curl -X POST http://localhost:8899/api/edges/check \
  -H "Content-Type: application/json" \
  -d '{"_from":"canonical_nodes/c:backend","_to":"canonical_nodes/t:java@21"}'
```

### 3. Логи

```bash
# API сервер
tail -f /tmp/graph_viewer_api.log
```

---

## 📝 Дальнейшее развитие

### Планируемые улучшения

1. **Исправить UPDATE endpoint** - устранить баг с обработкой результата
2. **Добавить веб-интерфейс** - кнопки создания/удаления связей в Graph Viewer
3. **Расширить валидацию** - проверка типов связей, обязательных полей
4. **Добавить аудит** - логирование всех операций со связями
5. **Batch операции** - массовое создание/удаление связей

### Предложения по интеграции

- Добавить контекстное меню в Graph Viewer для работы со связями
- Реализовать drag-and-drop для создания связей между узлами
- Добавить визуальную индикацию дублирующих связей
- Создать панель управления связями с фильтрами

---

## 📚 Связанная документация

- `docs-preliminary/chats/chat-2025-01-15-graph-structure-optimization.md` - Оптимизация структуры графа
- `docs-preliminary/project-history/chat-2025-10-17_trigger_arango.md` - История работы над триггерами
- `docs/project-documentation-rules.md` - Правила проектной документации

---

## ✅ Итоги

### Что реализовано

✅ **Валидация уникальности** - работает в обоих направлениях (A→B и B→A)  
✅ **REST API** - 4 endpoint'а для работы со связями  
✅ **MCP команды** - 4 команды для интеграции с Cursor  
✅ **Подробные сообщения** - указывают тип и ID дублирующей связи  
✅ **Автоматическая защита** - отклоняет дубликаты на уровне приложения  

### Готовность к использованию

**Статус:** ✅ **ГОТОВО К ИСПОЛЬЗОВАНИЮ**

Система валидации полностью функциональна и может использоваться для предотвращения дублирующих связей в графе проектов.

---

**Автор:** Claude (Cursor AI)  
**Дата:** 17 октября 2025  
**Версия документа:** 1.0

