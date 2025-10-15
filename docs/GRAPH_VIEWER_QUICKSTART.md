# Graph Viewer - Быстрый старт

Интерактивная система визуализации графов проектов fedoc.

---

## 🚀 Быстрый запуск

### Вариант 1: Через Python API (рекомендуется)

```python
cd /home/alex/fedoc
source venv/bin/activate

python3 -c "
import sys
sys.path.insert(0, 'src')
from mcp_server.handlers.graph_viewer_manager import open_graph_viewer

# Открыть для всех проектов
open_graph_viewer()
"
```

### Вариант 2: Через MCP сервер

```bash
cd /home/alex/fedoc/src/mcp_server
python3 server.py
```

Затем в Cursor AI:
```
Открой управление графом
```

---

## 📋 Основные команды

### Открыть визуализацию

**Все проекты:**
```python
from mcp_server.handlers.graph_viewer_manager import open_graph_viewer
open_graph_viewer()
```

**Конкретный проект:**
```python
open_graph_viewer(project='fepro')   # FEPRO
open_graph_viewer(project='femsq')   # FEMSQ
open_graph_viewer(project='fedoc')   # fedoc
```

**Без автоматического открытия браузера:**
```python
open_graph_viewer(auto_open_browser=False)
```

### Проверить статус

```python
from mcp_server.handlers.graph_viewer_manager import graph_viewer_status

status = graph_viewer_status()
print(status)
```

**Вывод:**
```
✅ Общий статус: running

🔧 Компоненты:
   ✅ ssh_tunnel: connected (PID: 2334)
   ✅ api_server: running (PID: 2744)
   ✅ vite_server: running (PID: 5173)

🌐 Интерфейс доступен: http://localhost:5173
```

### Остановить систему

```python
from mcp_server.handlers.graph_viewer_manager import stop_graph_viewer

# Остановить процессы (туннель оставить)
stop_graph_viewer()

# Остановить все включая туннель
stop_graph_viewer(stop_tunnel=True)

# Принудительная остановка
stop_graph_viewer(force=True)
```

---

## 🌐 Использование интерфейса

После запуска откроется браузер на `http://localhost:5173`

### Панель управления:

1. **Стартовая вершина** - выберите узел для начала построения графа
2. **Глубина обхода** - количество уровней связей (1-15)
3. **Фильтр по проекту** - fepro, femsq, fedoc или все
4. **Тема** - темная/светлая
5. **Обновить** - перестроить граф с новыми параметрами
6. **Подогнать** - автоматически подогнать размер

### Интерактивность:

- 🖱️ **Масштабирование** - колесо мыши
- 🖱️ **Перемещение** - перетаскивание
- 👆 **Клик на узел** - показать детали
- 🔍 **Наведение** - всплывающая подсказка

---

## 🔧 Что происходит при запуске?

```
open_graph_viewer()
    ↓
1. Проверка SSH туннеля к ArangoDB (176.108.244.252)
    └─ Создание туннеля если отсутствует
    ↓
2. Запуск API сервера (порт 8899)
    └─ REST API для получения данных графа
    ↓
3. Запуск Vite dev сервера (порт 5173)
    └─ Vue.js интерфейс
    ↓
4. Открытие браузера
    └─ http://localhost:5173
```

---

## ❓ Troubleshooting

### Проблема: "SSH туннель не создается"

```bash
# Проверить SSH доступ
ssh vuege-server

# Проверить существующие туннели
ps aux | grep "ssh.*8529"

# Создать туннель вручную
ssh -f -N -L 8529:localhost:8529 vuege-server
```

### Проблема: "API сервер не запускается"

```bash
# Проверить лог
cat /tmp/graph_viewer_api.log

# Проверить виртуальное окружение
source /home/alex/fedoc/venv/bin/activate
pip list | grep arango

# Установить зависимости
pip install python-arango
```

### Проблема: "Vite сервер не запускается"

```bash
# Проверить лог
cat /tmp/graph_viewer_vite.log

# Переустановить зависимости
cd /home/alex/fedoc/src/lib/graph_viewer/frontend
rm -rf node_modules package-lock.json
npm install
```

### Проблема: "Порт уже занят"

```bash
# Найти процесс на порту 5173
lsof -i :5173

# Остановить через stop_graph_viewer
python3 -c "
import sys
sys.path.insert(0, '/home/alex/fedoc/src')
from mcp_server.handlers.graph_viewer_manager import stop_graph_viewer
stop_graph_viewer(force=True)
"
```

---

## 📚 Дополнительная информация

- [Graph Viewer Backend](../src/lib/graph_viewer/backend/)
- [Graph Viewer Frontend](../src/lib/graph_viewer/frontend/)
- [MCP Server](../src/mcp_server/)
- [Архитектурное решение](decisions/GRAPH_VIEWER_MCP_INTEGRATION.md)

---

**Версия:** 0.2.0  
**Дата:** 2025-10-15











