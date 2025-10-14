# ArangoDB Graph Viewer

Интерактивное desktop приложение для просмотра графов из ArangoDB без создания файлов в проекте.

## 🚀 Быстрый старт

```bash
# Просмотреть весь граф
./view-graph.sh

# Просмотреть только проект fepro
./view-graph.sh --project fepro

# Просмотреть только проект femsq
./view-graph.sh --project femsq
```

Приложение автоматически:
1. Проверит SSH туннель к ArangoDB
2. Подключится к базе данных
3. Загрузит граф в реальном времени
4. Откроет интерактивную визуализацию в браузере

## 📋 Возможности

### 🎛️ Панель управления (встроенная в браузер):
- ✅ **Выбор стартовой вершины** - dropdown с популярными узлами
- ✅ **Глубина обхода** - слайдер от 1 до 15 рёбер
- ✅ **Фильтр по проекту** - fepro, femsq, fedoc или все
- ✅ **Переключение темы** - тёмная/светлая
- ✅ **Кнопка "Обновить"** - перезагрузить граф с новыми параметрами
- ✅ **Кнопка "Подогнать"** - автоматически подогнать размер
- ✅ **Счётчики** - количество узлов и рёбер в реальном времени

### Интерактивная визуализация:
- ✅ **Масштабирование** - колесо мыши
- ✅ **Перетаскивание** - мышь
- ✅ **Поиск узлов** - встроенный поиск
- ✅ **Информация о узлах** - наведение курсора
- ✅ **Цветовая кодировка**:
  - 🔵 Синие узлы - концептуальные (c:)
  - 🟢 Зелёные узлы - технологические (t:)
  - 🔵 Синие рёбра - реальные проекты
  - ⚪ Серые рёбра - альтернативные стеки

### Без артефактов:
- ✅ Не создаёт файлы в проекте fedoc
- ✅ Временный HTML файл в /tmp
- ✅ Данные загружаются напрямую из ArangoDB
- ✅ Всегда актуальная информация

## 🛠️ Использование

### Базовое использование:

```bash
# Весь граф
./view-graph.sh

# Только fepro (меньше узлов, быстрее)
./view-graph.sh --project fepro

# Только femsq
./view-graph.sh --project femsq
```

### Расширенное использование:

```bash
# Прямой вызов Python скрипта
python3 viewer.py \
    --password "aR@ng0Pr0d2025xK9mN8pL" \
    --graph "common_project_graph" \
    --project fepro \
    --start-node "canonical_nodes/c:backend" \
    --depth 5 \
    --theme dark \
    --output /tmp/my-graph.html

# От конкретной вершины на большую глубину
python3 viewer.py \
    --password "aR@ng0Pr0d2025xK9mN8pL" \
    --start-node "canonical_nodes/t:java@21" \
    --depth 10 \
    --theme light

# Не открывать браузер автоматически
python3 viewer.py \
    --password "aR@ng0Pr0d2025xK9mN8pL" \
    --no-browser
```

### 🎛️ Использование панели управления:

После открытия графа в браузере:

1. **Выберите стартовую вершину** из dropdown (например, "c:backend")
2. **Установите глубину** слайдером (1-15 рёбер)
3. **Выберите проект** или оставьте "Все проекты"
4. **Переключите тему** (🌙 Тёмная / ☀️ Светлая)
5. **Нажмите "🔄 Обновить"** для перезагрузки графа
6. **Нажмите "📐 Подогнать"** для автоматического масштабирования

Все изменения применяются мгновенно без перезапуска приложения!

## 📐 Параметры командной строки

```
--host       Хост ArangoDB (default: http://localhost:8529)
--db         База данных (default: fedoc)
--user       Пользователь (default: root)
--password   Пароль (обязательный)
--graph      Имя графа (default: common_project_graph)
--project    Фильтр по проекту (fepro, femsq, fedoc)
--output     Выходной HTML файл (default: /tmp/arango-graph.html)
--max-nodes  Максимум узлов (default: 1000)
--no-browser Не открывать браузер
```

## 🎯 Преимущества

| Характеристика | ArangoDB Web UI | Graph Viewer |
|----------------|-----------------|--------------|
| Качество визуализации | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Интерактивность | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Скорость работы | ⭐⭐ | ⭐⭐⭐⭐ |
| Удобство | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Фильтрация | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Артефакты в проекте | Нет | Нет |

## 🔧 Технические детали

### Архитектура:
```
ArangoDB (localhost:8529)
    ↓
Python Script (viewer.py)
    ↓
PyVis (генерация HTML)
    ↓
Браузер (интерактивная визуализация)
```

### Зависимости:
- Python 3.13+
- python-arango
- pyvis
- networkx
- matplotlib

### Где хранятся файлы:
- **Скрипты**: `/home/alex/tools/arango-graph-viewer/`
- **Временный HTML**: `/tmp/arango-graph.html`
- **Проект fedoc**: НЕ ЗАСОРЯЕТСЯ ✅

## 🔄 Обновление графа

Просто запустите скрипт заново - он всегда загружает актуальные данные из ArangoDB:

```bash
./view-graph.sh
```

## 📚 Примеры

### Исследование архитектуры FEPRO:
```bash
./view-graph.sh --project fepro
# Откроется граф с путями:
# - Backend → Java → Spring Boot → API → GraphQL
# - Backend → Java → Spring Boot → Security → JWT + Spring Security
# - Backend → Java → Spring Boot → Cache → Hazelcast + Caffeine
# И т.д.
```

### Сравнение FEPRO и FEMSQ:
```bash
# Сначала посмотреть FEPRO
./view-graph.sh --project fepro

# Затем посмотреть FEMSQ
./view-graph.sh --project femsq

# Заметить различия в Security:
# FEPRO: With Security → JWT + Spring Security
# FEMSQ: No Security
```

### Просмотр всей картины:
```bash
# Все проекты и альтернативные стеки
./view-graph.sh
```

## 🆘 Troubleshooting

### Проблема: "Connection refused"
```bash
# Проверить SSH туннель
ps aux | grep "ssh.*8529"

# Создать туннель вручную
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N &
```

### Проблема: "Authentication failed"
```bash
# Проверить пароль в скрипте view-graph.sh
# Или передать явно:
python3 viewer.py --password "ваш_пароль"
```

### Проблема: Граф не отображается
```bash
# Проверить, что граф существует в ArangoDB
curl -u root:aR@ng0Pr0d2025xK9mN8pL \
    http://localhost:8529/_api/database/fedoc
```

## 🔗 Полезные ссылки

- [PyVis Documentation](https://pyvis.readthedocs.io/)
- [ArangoDB Graphs](https://www.arangodb.com/docs/stable/graphs.html)
- [NetworkX Documentation](https://networkx.org/)

---

**Создано**: 2025-10-14  
**Автор**: Александр  
**Для проекта**: fedoc

