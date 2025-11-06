# Решения для длинных ключей узлов

**Дата**: 2025-11-05  
**Статус**: Предложение  
**Приоритет**: Высокий

---

## Проблема

При использовании формата `{segment}.{type}.{identifier}` ключи для структуры кода и файловой системы могут стать очень длинными:

**Примеры проблемных ключей**:
- `c.m.lib.graph_viewer.backend.api_server` (42 символа)
- `f.d.src/lib/graph_viewer/backend/api_server` (38 символов)
- `f.file.src/lib/graph_viewer/backend/api_server.py` (45 символов)
- `c.nested.GraphObject.Validator.ValidationRule` (40 символов)

**Проблемы**:
- ❌ Длинные ключи в БД (занимают больше места)
- ❌ Медленнее индексация и поиск
- ❌ Неудобно в API и логах
- ❌ Ограничения длины ключа в некоторых БД

---

## Решения

### Решение 1: Короткие идентификаторы (рекомендуется)

**Идея**: Использовать короткие, но уникальные идентификаторы вместо полных путей.

#### Для модулей

**Вместо**:
- `c.m.lib.graph_viewer` (22 символа)
- `c.m.lib.graph_viewer.backend` (30 символов)
- `c.m.lib.graph_viewer.backend.api_server` (42 символа)

**Использовать**:
- `c.m.graph_viewer` (18 символов)
- `c.m.graph_viewer_backend` (25 символов)
- `c.m.api_server_age` (19 символов)

**Правила**:
- Убрать общие префиксы (`lib.`, `src/`)
- Использовать короткие, но понятные имена
- Сохранить иерархию через связи в графе

#### Для файлов

**Вместо**:
- `f.file.src/lib/graph_viewer/backend/api_server.py` (45 символов)

**Использовать**:
- `f.file.api_server_age` (19 символов)

**Полный путь хранить в properties**:
```json
{
  "key": "f.file.api_server_age",
  "name": "api_server.py",
  "properties": {
    "path": "src/lib/graph_viewer/backend/api_server.py",
    "directory": "f.d.graph_viewer_backend"
  }
}
```

#### Для директорий

**Вместо**:
- `f.d.src/lib/graph_viewer/backend` (32 символа)

**Использовать**:
- `f.d.graph_viewer_backend` (25 символов)

**Полный путь в properties**:
```json
{
  "key": "f.d.graph_viewer_backend",
  "name": "backend",
  "properties": {
    "path": "src/lib/graph_viewer/backend",
    "parent": "f.d.graph_viewer"
  }
}
```

**Преимущества**:
- ✅ Короткие ключи (15-25 символов)
- ✅ Понятные имена
- ✅ Полная информация в properties
- ✅ Иерархия через связи в графе

---

### Решение 2: Хеширование для очень длинных путей

**Идея**: Использовать хеш для идентификатора, полный путь хранить в properties.

#### Алгоритм

```python
import hashlib

def create_file_key(file_path: str) -> str:
    """
    Создать короткий ключ для файла
    
    Args:
        file_path: Полный путь к файлу
    
    Returns:
        Короткий ключ: f.file.{hash}
    """
    # Создать хеш от пути
    path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
    
    # Извлечь имя файла для читаемости
    file_name = file_path.split('/')[-1].replace('.py', '').replace('.js', '')
    file_name_short = file_name[:10]  # Первые 10 символов
    
    # Комбинировать: имя + хеш
    return f"f.file.{file_name_short}_{path_hash}"

# Примеры
create_file_key("src/lib/graph_viewer/backend/api_server.py")
# → "f.file.api_server_a1b2c3d4"

create_file_key("src/lib/graph_traversal/markdown_generator.py")
# → "f.file.markdown_g_5e6f7g8h"
```

**Структура узла**:
```json
{
  "key": "f.file.api_server_a1b2c3d4",
  "name": "api_server.py",
  "properties": {
    "path": "src/lib/graph_viewer/backend/api_server.py",
    "full_path_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
  }
}
```

**Преимущества**:
- ✅ Очень короткие ключи (20-25 символов)
- ✅ Гарантированная уникальность через хеш
- ✅ Полный путь в properties

**Недостатки**:
- ⚠️ Менее читаемо (есть хеш)
- ⚠️ Нужна функция для поиска по пути

---

### Решение 3: Иерархические ключи с сокращениями

**Идея**: Использовать сокращения для общих частей пути.

#### Правила сокращений

```python
# Словарь сокращений
ABBREVIATIONS = {
    'graph_viewer': 'gv',
    'graph_traversal': 'gt',
    'mcp_server': 'mcp',
    'api_server': 'api',
    'backend': 'be',
    'frontend': 'fe',
    'lib': 'l',
    'src': 's'
}

def abbreviate_path(path: str) -> str:
    """Сократить путь используя словарь"""
    parts = path.split('/')
    abbreviated = [ABBREVIATIONS.get(p, p[:3]) for p in parts]
    return '.'.join(abbreviated)

# Примеры
abbreviate_path("src/lib/graph_viewer/backend")
# → "s.l.gv.be"

abbreviate_path("src/lib/graph_viewer/backend/api_server")
# → "s.l.gv.be.api"
```

**Ключи**:
- `f.d.s.l.gv.be` вместо `f.d.src/lib/graph_viewer/backend`
- `c.m.gv` вместо `c.m.lib.graph_viewer`

**Преимущества**:
- ✅ Очень короткие ключи (10-15 символов)
- ✅ Сохраняет структуру

**Недостатки**:
- ⚠️ Менее читаемо
- ⚠️ Нужен словарь сокращений
- ⚠️ Риск коллизий

---

### Решение 4: Комбинированный подход (рекомендуется)

**Идея**: Комбинация коротких идентификаторов + полных путей в properties.

#### Правила

1. **Модули**: Короткие имена без общих префиксов
   - `c.m.graph_viewer` (не `c.m.lib.graph_viewer`)
   - `c.m.api_server_age` (не `c.m.lib.graph_viewer.backend.api_server_age`)

2. **Компоненты**: Короткие имена с контекстом
   - `c.comp.api_server_age` (не `c.comp.lib.graph_viewer.backend.api_server_age`)

3. **Классы**: Полное имя класса
   - `c.class.GraphObject` (короткое и понятное)
   - `c.nested.GraphObject.Validator` (приемлемая длина)

4. **Директории**: Короткие имена
   - `f.d.graph_viewer` (не `f.d.src/lib/graph_viewer`)
   - `f.d.graph_viewer_backend` (не `f.d.src/lib/graph_viewer/backend`)

5. **Файлы**: Имя файла + контекст
   - `f.file.api_server_age` (не `f.file.src/lib/graph_viewer/backend/api_server.py`)

#### Полная информация в properties

```json
{
  "key": "f.file.api_server_age",
  "name": "api_server.py",
  "properties": {
    "path": "src/lib/graph_viewer/backend/api_server.py",
    "directory_key": "f.d.graph_viewer_backend",
    "module_key": "c.m.graph_viewer_backend"
  }
}
```

#### Иерархия через связи

```
f.d.graph_viewer (parent)
  └─→ f.d.graph_viewer_backend (child)
      └─→ f.file.api_server_age (file in directory)
```

**Связи**:
- `f.d.graph_viewer` → `f.d.graph_viewer_backend` (contains)
- `f.d.graph_viewer_backend` → `f.file.api_server_age` (contains)
- `c.m.graph_viewer_backend` → `f.d.graph_viewer_backend` (mapped_to)

---

## Рекомендуемый подход

### Правила создания ключей

#### 1. Модули (`c.m.*`)

**Правило**: Убрать общие префиксы, использовать короткие имена.

```python
# Полный путь: src/lib/graph_viewer
# Ключ: c.m.graph_viewer

# Полный путь: src/lib/graph_viewer/backend
# Ключ: c.m.graph_viewer_backend (или c.m.graph_viewer_be)

# Полный путь: src/mcp_server/handlers
# Ключ: c.m.mcp_server_handlers (или c.m.mcp_handlers)
```

#### 2. Компоненты (`c.comp.*`)

**Правило**: Имя компонента без пути.

```python
# Файл: src/lib/graph_viewer/backend/api_server_age.py
# Ключ: c.comp.api_server_age

# Файл: src/lib/graph_traversal/markdown_generator.py
# Ключ: c.comp.markdown_generator
```

#### 3. Классы (`c.class.*`, `c.nested.*`)

**Правило**: Полное имя класса (уже короткое).

```python
# Класс: GraphObject
# Ключ: c.class.GraphObject

# Класс: GraphObject.Validator
# Ключ: c.nested.GraphObject.Validator
```

#### 4. Директории (`f.d.*`)

**Правило**: Короткое имя без общих префиксов.

```python
# Путь: src/lib/graph_viewer
# Ключ: f.d.graph_viewer

# Путь: src/lib/graph_viewer/backend
# Ключ: f.d.graph_viewer_backend

# Путь: src/mcp_server/handlers
# Ключ: f.d.mcp_server_handlers
```

#### 5. Файлы (`f.file.*`)

**Правило**: Имя файла без расширения + контекст при необходимости.

```python
# Файл: src/lib/graph_viewer/backend/api_server_age.py
# Ключ: f.file.api_server_age

# Файл: src/lib/graph_viewer/backend/config_manager.py
# Ключ: f.file.config_manager

# Если есть коллизии, добавить контекст:
# f.file.api_server_age_gv (graph_viewer)
```

---

## Примеры ключей

### Архитектура (короткие, проблем нет)
- `a.c.project` (12 символов)
- `a.c.backend` (12 символов)
- `a.t.python` (11 символов)
- `a.v.python@3.12` (16 символов)

### Структура кода (сокращённые)
- `c.m.graph_viewer` (19 символов) ✅
- `c.m.graph_viewer_backend` (26 символов) ✅
- `c.m.api_server_age` (19 символов) ✅
- `c.comp.api_server_age` (20 символов) ✅
- `c.class.GraphObject` (19 символов) ✅
- `c.nested.GraphObject.Validator` (31 символ) ⚠️ (приемлемо)

### Файловая система (сокращённые)
- `f.d.graph_viewer` (18 символов) ✅
- `f.d.graph_viewer_backend` (25 символов) ✅
- `f.file.api_server_age` (20 символов) ✅
- `f.file.config_manager` (22 символа) ✅

**Все ключи в пределах 12-31 символа** — приемлемо!

---

## Функция нормализации ключей

```python
# utils/key_normalizer.py
def normalize_module_key(full_path: str) -> str:
    """
    Нормализовать путь модуля в короткий ключ
    
    Args:
        full_path: Полный путь (например, "src/lib/graph_viewer")
    
    Returns:
        Короткий ключ (например, "graph_viewer")
    """
    # Убрать общие префиксы
    path = full_path
    for prefix in ['src/', 'lib/', 'src/lib/']:
        if path.startswith(prefix):
            path = path[len(prefix):]
    
    # Заменить '/' на '_'
    path = path.replace('/', '_')
    
    # Сократить если слишком длинный
    if len(path) > 25:
        parts = path.split('_')
        # Взять последние значимые части
        path = '_'.join(parts[-3:])
    
    return path

def normalize_file_key(file_path: str) -> str:
    """
    Нормализовать путь файла в короткий ключ
    
    Args:
        file_path: Полный путь (например, "src/lib/graph_viewer/backend/api_server_age.py")
    
    Returns:
        Короткий ключ (например, "api_server_age")
    """
    # Извлечь имя файла
    file_name = file_path.split('/')[-1]
    
    # Убрать расширение
    file_name = file_name.replace('.py', '').replace('.js', '').replace('.ts', '')
    
    return file_name

def normalize_directory_key(dir_path: str) -> str:
    """
    Нормализовать путь директории в короткий ключ
    
    Args:
        dir_path: Полный путь (например, "src/lib/graph_viewer/backend")
    
    Returns:
        Короткий ключ (например, "graph_viewer_backend")
    """
    # Убрать общие префиксы
    path = dir_path
    for prefix in ['src/', 'lib/', 'src/lib/']:
        if path.startswith(prefix):
            path = path[len(prefix):]
    
    # Заменить '/' на '_'
    path = path.replace('/', '_')
    
    # Сократить если слишком длинный
    if len(path) > 25:
        parts = path.split('_')
        path = '_'.join(parts[-2:])  # Последние 2 части
    
    return path

# Примеры использования
normalize_module_key("src/lib/graph_viewer")
# → "graph_viewer"

normalize_file_key("src/lib/graph_viewer/backend/api_server_age.py")
# → "api_server_age"

normalize_directory_key("src/lib/graph_viewer/backend")
# → "graph_viewer_backend"
```

---

## Сравнение подходов

| Подход | Длина ключа | Читаемость | Уникальность | Сложность |
|--------|------------|------------|--------------|-----------|
| **Полный путь** | 30-50 символов | ✅ Отлично | ✅ Гарантирована | ❌ Слишком длинно |
| **Короткие идентификаторы** | 15-25 символов | ✅ Хорошо | ✅ Гарантирована | ✅ Просто |
| **Хеширование** | 20-25 символов | ⚠️ Средне | ✅ Гарантирована | ⚠️ Средне |
| **Сокращения** | 10-15 символов | ⚠️ Плохо | ⚠️ Риск коллизий | ⚠️ Сложно |
| **Комбинированный** | 15-30 символов | ✅ Хорошо | ✅ Гарантирована | ✅ Просто |

---

## Рекомендация

**Использовать комбинированный подход**:

1. **Короткие идентификаторы** для модулей, компонентов, директорий, файлов
2. **Полные пути в properties** для восстановления контекста
3. **Иерархия через связи** в графе
4. **Функции нормализации** для автоматического создания коротких ключей

**Результат**:
- ✅ Ключи 15-30 символов (приемлемо)
- ✅ Читаемость сохранена
- ✅ Уникальность гарантирована
- ✅ Полная информация доступна через properties

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

