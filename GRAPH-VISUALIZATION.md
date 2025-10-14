# Визуализация общего графа проектов

Этот документ описывает альтернативные способы визуализации графа проектов из ArangoDB.

## 📊 Созданные файлы

### 1. Graphviz (DOT) - **РЕКОМЕНДУЕТСЯ**

**Файлы:**
- `common-project-graph.dot` - исходный DOT файл
- `common-project-graph.png` - PNG изображение (250 KB)
- `common-project-graph.svg` - SVG изображение (37 KB, масштабируемое)

**Как просмотреть:**
```bash
# Открыть PNG
xdg-open common-project-graph.png

# Открыть SVG в браузере (лучше масштабируется)
firefox common-project-graph.svg

# Или в любом редакторе, поддерживающем SVG
inkscape common-project-graph.svg
```

**Как редактировать и пересоздать:**
```bash
# Редактировать DOT файл
nano common-project-graph.dot

# Пересоздать изображения
dot -Tpng common-project-graph.dot -o common-project-graph.png
dot -Tsvg common-project-graph.dot -o common-project-graph.svg

# Другие форматы
dot -Tpdf common-project-graph.dot -o common-project-graph.pdf
dot -Tjpg common-project-graph.dot -o common-project-graph.jpg
```

**Преимущества:**
- ✅ Автоматическая компоновка узлов
- ✅ Высокое качество изображений
- ✅ Поддержка множества форматов вывода
- ✅ Легко редактировать структуру

### 2. Mermaid диаграммы

**Файл:** `common-project-graph.mmd`

**Как просмотреть:**

1. **В онлайн редакторе:**
   - Откройте https://mermaid.live/
   - Скопируйте содержимое `common-project-graph.mmd`
   - Вставьте в редактор

2. **В VS Code:**
   - Установите расширение "Markdown Preview Mermaid Support"
   - Создайте `.md` файл и вставьте:
     ````markdown
     ```mermaid
     <содержимое common-project-graph.mmd>
     ```
     ````

3. **В командной строке:**
   ```bash
   # Установить Mermaid CLI
   npm install -g @mermaid-js/mermaid-cli
   
   # Сгенерировать изображение
   mmdc -i common-project-graph.mmd -o common-project-graph-mermaid.png
   ```

**Преимущества:**
- ✅ Интеграция с Markdown
- ✅ Интерактивность в онлайн редакторе
- ✅ Хорошая поддержка в GitHub/GitLab

### 3. Текстовые деревья

**Файлы:**
- `common-project-graph-fepro.txt` - дерево проекта FEPRO
- `common-project-graph-femsq.txt` - дерево проекта FEMSQ

**Как просмотреть:**
```bash
# В терминале
cat common-project-graph-fepro.txt

# С постраничным выводом
less common-project-graph-fepro.txt

# В редакторе
nano common-project-graph-fepro.txt
```

**Преимущества:**
- ✅ Простота
- ✅ Быстрый поиск (grep)
- ✅ Копирование в документы
- ✅ Не требует дополнительных инструментов

## 🔄 Регенерация визуализаций

Если граф изменился, можно пересоздать визуализации:

```python
# Подключиться к ArangoDB
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fedoc', username='root', password='aR@ng0Pr0d2025xK9mN8pL')

# Запустить скрипт генерации (см. выше в чате)
```

Или использовать готовый скрипт (если создан).

## 📐 Сравнение методов

| Метод | Качество | Интерактивность | Редактирование | Размер файла |
|-------|----------|-----------------|----------------|--------------|
| **Graphviz (PNG)** | ⭐⭐⭐⭐⭐ | ❌ | ✅ (через DOT) | 250 KB |
| **Graphviz (SVG)** | ⭐⭐⭐⭐⭐ | ⭐ (масштаб) | ✅ (через DOT) | 37 KB |
| **Mermaid** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | 3 KB |
| **Текстовое дерево** | ⭐⭐⭐ | ❌ | ✅ | 6 KB |
| **ArangoDB Web UI** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | - |

## 🎯 Рекомендации

### Для просмотра структуры:
1. **SVG файл** - лучшее качество и масштабирование
2. **Текстовое дерево** - быстрый обзор конкретного проекта

### Для презентаций:
1. **PNG файл** - вставка в слайды
2. **Mermaid** - для документации в Markdown

### Для редактирования:
1. **DOT файл** - редактировать и пересоздавать PNG/SVG
2. **Mermaid** - быстрое прототипирование

## 🛠️ Дополнительные инструменты

### Интерактивные просмотрщики DOT:

```bash
# xdot - интерактивный просмотрщик
sudo dnf install xdot
xdot common-project-graph.dot

# gvedit - редактор Graphviz
gvedit common-project-graph.dot
```

### Онлайн инструменты:

- **Graphviz Online**: http://www.webgraphviz.com/
- **Mermaid Live**: https://mermaid.live/
- **D3.js Graph Visualizer**: https://observablehq.com/

## 📝 Примечания

- Все файлы используют UTF-8 кодировку для поддержки русского языка
- SVG файлы можно открывать в любом современном браузере
- DOT файлы можно редактировать в любом текстовом редакторе
- Для больших графов рекомендуется использовать SVG вместо PNG

## 🔗 Полезные ссылки

- [Graphviz Documentation](https://graphviz.org/documentation/)
- [Mermaid Documentation](https://mermaid.js.org/)
- [DOT Language Guide](https://graphviz.org/doc/info/lang.html)


