# ArangoDB Legacy Read-Only Access

## ⚠️ Статус
**ArangoDB больше не используется в проекте FEDoc с версии 2025-10-18.**

Вся функциональность была перенесена на **PostgreSQL + Apache AGE**.

## 📖 Назначение документа
Этот документ описывает, как получить read-only доступ к legacy-данным ArangoDB для:
- Проверки данных при миграции
- Восстановления исторических данных
- Отладки проблем, возникших после миграции

## 🔌 Подключение к ArangoDB

### Вариант 1: SSH туннель + ArangoDB Web UI
```bash
# Создать SSH туннель на порт 8529
ssh -f -N -L 8529:localhost:8529 fedoc-server

# Открыть в браузере
http://localhost:8529
```

**Учетные данные:**
- **Username:** `root`
- **Password:** *(запросите у администратора)*
- **Database:** `fedoc`

### Вариант 2: Python-скрипт (read-only)
```python
from arango import ArangoClient

# Подключение через SSH туннель
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fedoc', username='root', password='YOUR_PASSWORD')

# Чтение узлов
nodes = list(db.collection('canonical_nodes').all())
print(f"Всего узлов: {len(nodes)}")

# Чтение рёбер
edges = list(db.collection('project_relations').all())
print(f"Всего рёбер: {len(edges)}")

# Чтение проектов
projects = list(db.collection('projects').all())
print(f"Всего проектов: {len(projects)}")
```

### Вариант 3: cURL (для быстрых запросов)
```bash
# Получить список коллекций
curl -u root:PASSWORD http://localhost:8529/_db/fedoc/_api/collection

# Получить все узлы (первые 100)
curl -u root:PASSWORD http://localhost:8529/_db/fedoc/_api/simple/all \
  -X PUT -H "Content-Type: application/json" \
  -d '{"collection":"canonical_nodes","limit":100}'
```

## 📊 Структура данных ArangoDB

### Коллекции
1. **`canonical_nodes`** - Канонические узлы графа (39 узлов)
   - `_key`: Уникальный ключ узла (например, `c:project`, `t:java`)
   - `name`: Название узла
   - `kind`: Тип узла (category, technology, version)

2. **`project_relations`** - Рёбра графа (34 ребра)
   - `_from`: ID исходного узла
   - `_to`: ID целевого узла
   - `projects`: Массив проектов, использующих эту связь
   - `relationType`: Тип связи (например, "related", "alternative")

3. **`projects`** - Документы проектов (4 документа)
   - `_key`: Уникальный ключ проекта (например, `fedoc`, `fepro`)
   - `name`: Название проекта
   - `description`: Описание
   - *(другие поля)*

4. **`rules`** - Правила проектов (10 документов)
   - `_key`: Уникальный ключ правила
   - `name`: Название правила
   - `data`: JSONB-данные

## 🔄 Сопоставление с PostgreSQL

### Граф (canonical_nodes → project_relations)
**ArangoDB:**
```aql
FOR v, e, p IN 1..5 OUTBOUND 'canonical_nodes/c:project'
  project_relations
  RETURN {vertex: v, edge: e}
```

**PostgreSQL + AGE:**
```sql
SELECT * FROM ag_catalog.get_graph_for_viewer('c:project', 5);
```

### Документы (projects, rules)
**ArangoDB:**
```javascript
db.projects.document('fedoc')
```

**PostgreSQL:**
```sql
SELECT * FROM projects WHERE key = 'fedoc';
```

## 🚫 Ограничения

### Read-Only режим
**⚠️ ВАЖНО:** ArangoDB используется ТОЛЬКО для чтения.

**НЕ ВЫПОЛНЯЙТЕ:**
- `INSERT`, `UPDATE`, `DELETE` операции
- Создание/удаление коллекций
- Изменение индексов
- Любые модификации данных

**Причина:** Все изменения должны идти через PostgreSQL. ArangoDB - это только legacy-источник данных.

## 🛠️ Утилиты для работы с legacy-данными

### Скрипт проверки консистентности
```bash
# Сравнить количество объектов
python scripts/check-arango-data.py

# Вывод:
# ArangoDB nodes: 39
# PostgreSQL nodes: 39
# ✓ Консистентно
```

### Скрипт экспорта данных
```bash
# Экспортировать все данные из ArangoDB в JSON
python scripts/export-arango-to-json.py --output /tmp/arango-backup.json
```

## 📝 Когда использовать ArangoDB legacy-доступ

### ✅ Хорошие сценарии:
- Верификация данных после миграции
- Восстановление удаленных данных (если есть резервная копия)
- Отладка несоответствий между старыми и новыми данными
- Анализ исторических данных

### ❌ Плохие сценарии:
- Использование ArangoDB для production-операций
- Запись новых данных в ArangoDB
- Синхронизация данных между ArangoDB и PostgreSQL
- Использование ArangoDB как primary-источник данных

## 🗑️ План вывода из эксплуатации

### Фаза 1: Текущая (до 2025-12-31)
- ArangoDB доступен в read-only режиме
- PostgreSQL - primary база данных
- Все новые данные идут в PostgreSQL

### Фаза 2: Архивация (2026-01-01 - 2026-03-31)
- Создание полного dump ArangoDB
- Перенос dump на архивное хранилище
- Отключение ArangoDB контейнера на production

### Фаза 3: Полное удаление (после 2026-04-01)
- Удаление ArangoDB из Docker Compose
- Удаление зависимостей `python-arango` из `requirements.txt`
- Удаление legacy-скриптов миграции

## 📞 Контакты
Если вам нужен доступ к legacy-данным ArangoDB:
1. Убедитесь, что данные не доступны в PostgreSQL
2. Создайте задачу с описанием, зачем нужен доступ
3. Запросите учетные данные у администратора

---
**Версия документа:** 1.0  
**Дата создания:** 2025-10-20  
**Последнее обновление:** 2025-10-20


