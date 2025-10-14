# Визуализации общего графа проектов

Эта папка содержит различные форматы визуализации общего графа проектов из ArangoDB.

## 📁 Файлы

### 1. Graphviz (рекомендуется)

- **`common-project-graph.dot`** (5.7 KB) - исходный DOT файл
- **`common-project-graph.png`** (250 KB) - PNG изображение
- **`common-project-graph.svg`** (37 KB) - SVG изображение (масштабируемое)

**Как просмотреть:**
```bash
xdg-open common-project-graph.png
firefox common-project-graph.svg
```

### 2. Mermaid

- **`common-project-graph.mmd`** (2.9 KB) - Mermaid диаграмма

**Как просмотреть:**
- Онлайн: https://mermaid.live/
- В VS Code с расширением "Markdown Preview Mermaid Support"

### 3. Текстовые деревья

- **`common-project-graph-fepro.txt`** (5.8 KB) - дерево проекта FEPRO
- **`common-project-graph-femsq.txt`** (2.9 KB) - дерево проекта FEMSQ

**Как просмотреть:**
```bash
cat common-project-graph-fepro.txt
less common-project-graph-fepro.txt
```

### 4. Документация

- **`GRAPH-VISUALIZATION.md`** - полная инструкция по визуализации

---

## 🚀 Быстрый старт

### Просмотреть граф:

```bash
# Лучший вариант - масштабируемый SVG
firefox docs/visualizations/common-project-graph.svg

# Или PNG
xdg-open docs/visualizations/common-project-graph.png

# Текстовое дерево проекта
cat docs/visualizations/common-project-graph-fepro.txt
```

### Интерактивный просмотр (рекомендуется):

```bash
cd /home/alex/tools/arango-graph-viewer
./view-graph.sh
```

Откроется интерактивный граф с Tom-Select комбобоксом для выбора стартовой вершины.

---

## 🔄 Регенерация

Если граф в ArangoDB изменился, можно пересоздать визуализации:

```python
# Подключиться к ArangoDB
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fedoc', username='root', password='пароль')

# Сгенерировать DOT файл
# ... код генерации ...

# Создать изображения
dot -Tpng common-project-graph.dot -o common-project-graph.png
dot -Tsvg common-project-graph.dot -o common-project-graph.svg
```

Или использовать Graph Viewer - он всегда показывает актуальные данные из ArangoDB.

---

## 📊 Что визуализируется

### Структура графа:

- **38 узлов** (17 концептуальных + 21 технологический)
- **62 рёбра** (47 реальных + 15 альтернативных)
- **3 проекта** (fepro, femsq, fedoc)

### Архитектура:

```
Backend → Stack → Language → Framework → Elements
  ├─ Java → Spring Boot → [API, Security, Cache, Reactive, Migrations, Monitoring]
  ├─ Python → FastAPI → [API, Security, Migrations, Monitoring] (альтернатива)
  └─ Node.js → Express → [API, Security] (альтернатива)
```

### Цветовая кодировка:

- 🔵 **Синие узлы** - концептуальные (c:)
- 🟢 **Зелёные узлы** - технологические (t:)
- 🔵 **Синие рёбра** - реальные проекты
- ⚪ **Серые рёбра** - альтернативные стеки

---

## 🔗 См. также

- [GRAPH-VISUALIZATION.md](GRAPH-VISUALIZATION.md) - подробные инструкции
- [../../project-history/chat-2025-10-14-common-project-graph.md](../project-history/chat-2025-10-14-common-project-graph.md) - отчёт о создании
- [../../chats/chat-2025-10-14-common-project-graph-full.md](../chats/chat-2025-10-14-common-project-graph-full.md) - полный текст чата

---

**Обновлено:** 2025-10-14  
**Граф:** common_project_graph  
**База данных:** ArangoDB fedoc

