# Контекст для нового чата: Миграция на Vue.js

**Дата:** 2025-10-15  
**Текущая ветка:** `feature/vue-migration`  
**Предыдущий чат:** Разработка Graph Viewer на Alpine.js

---

## 📍 Текущая ситуация

### Что сделано в предыдущем чате:
1. ✅ **Alpine.js + Vite фронтенд работает**
   - Визуализация графа через vis-network
   - Панель деталей с навигацией
   - Разворачивание связанных документов
   - Сокращение имён коллекций
   - Панель полного текста
   - Resizable панель
   - Светлая/тёмная темы

2. ✅ **REST API сервер работает**
   - `api_server.py` на порту 8899
   - Endpoints: `/nodes`, `/graph`, `/object_details`

3. ✅ **Проблемы Alpine.js выявлены**
   - Монолитная архитектура (500+ строк в main.js)
   - Проблемы с реактивностью
   - Ограниченная масштабируемость

4. ✅ **Решение принято: миграция на Vue.js 3**
   - Создана ветка `feature/vue-migration`
   - План миграции готов (7 этапов, 7-11 часов)
   - Анализ фреймворков завершён

---

## 📂 Важные файлы

### Документация
- `docs/decisions/frontend-framework-analysis.md` - детальный анализ фреймворков (React vs Vue.js vs Svelte)
- `docs/decisions/vue-migration-plan.md` - **ГЛАВНЫЙ ДОКУМЕНТ** с планом миграции (747 строк)
- `src/lib/graph_viewer/frontend/ARCHITECTURE.md` - описание текущей Alpine.js архитектуры

### Рабочий код
- `src/lib/graph_viewer/api_server.py` - REST API (БЕЗ ИЗМЕНЕНИЙ)
- `src/lib/graph_viewer/frontend/` - текущий Alpine.js код (БУДЕТ СОХРАНЁН как frontend-alpine)
- `src/lib/graph_viewer/frontend/src/main.js` - монолит Alpine.js (500+ строк)
- `src/lib/graph_viewer/frontend/src/style.css` - стили (КОПИРОВАТЬ в Vue.js)

---

## 🚀 Следующие шаги (для нового чата)

### Этап 1: Настройка проекта (0.5-1ч) - **НАЧАТЬ С ЭТОГО**

**Задачи:**
1. Переименовать `frontend/` → `frontend-alpine/` (бэкап)
2. Создать новый Vue.js проект:
   ```bash
   cd src/lib/graph_viewer
   mv frontend frontend-alpine
   npm create vite@latest frontend -- --template vue
   cd frontend
   npm install
   npm install vis-network vis-data pinia
   ```
3. Скопировать стили из `frontend-alpine/src/style.css`
4. Настроить Vite config (API proxy на 8899)

### Этап 2-7: См. vue-migration-plan.md

---

## 🔧 Технические детали

### API Backend
- **URL:** `http://127.0.0.1:8899`
- **Endpoints:**
  - `GET /nodes?project=<name>` - список узлов
  - `GET /graph?start_node=<id>&depth=<n>&project=<name>` - граф
  - `GET /object_details?object_id=<id>` - детали объекта

### ArangoDB
- **URL:** `http://localhost:8529`
- **Database:** `fedoc`
- **Коллекции:**
  - `canonical_nodes` - узлы графа
  - `project_relations` - связи
  - `projects` - проекты
  - `rules` - правила

### Запуск API сервера
```bash
cd /home/alex/projects/rules/fedoc/src/lib/graph_viewer
python3 api_server.py --db-password "aR@ng0Pr0d2025xK9mN8pL" --port 8899
```

### Запуск Vite dev server (Alpine.js - текущий)
```bash
cd /home/alex/projects/rules/fedoc/src/lib/graph_viewer/frontend
npm run dev
# http://localhost:5173
```

---

## 📋 Стек Vue.js (целевой)

```
Vue.js 3 + Vite
├── Composition API       # ref(), computed(), watch()
├── Pinia                # State management
├── vis-network          # Визуализация графа (без изменений)
├── vis-data             # DataSet для графа
└── CSS (из Alpine.js)   # Копировать стили
```

---

## 🎯 Цели миграции

1. **Компонентная архитектура** - разбить монолит на компоненты
2. **Масштабируемость** - готовность к расширению функционала
3. **Реактивность** - нативная поддержка из коробки
4. **Поддержка** - легче добавлять новые функции

---

## 📊 Оценка времени

| Этап | Время | Статус |
|------|-------|--------|
| 1. Настройка проекта | 0.5-1 ч | ⏳ Начать |
| 2. Базовые компоненты | 1-2 ч | ⏳ |
| 3. vis-network | 1-2 ч | ⏳ |
| 4. Панель деталей | 2-3 ч | ⏳ |
| 5. Pinia store | 1 ч | ⏳ |
| 6. Утилиты и стили | 0.5-1 ч | ⏳ |
| 7. Тестирование | 1 ч | ⏳ |
| **ИТОГО** | **7-11 ч** | |

---

## 💡 Для AI ассистента в новом чате

**Приоритеты:**
1. Следовать плану из `vue-migration-plan.md`
2. Сохранить весь функционал из Alpine.js версии
3. Использовать Composition API (не Options API)
4. Использовать Pinia для state management
5. Копировать стили без изменений (сначала)

**Важно:**
- API сервер на порту 8899 работает, НЕ МЕНЯТЬ
- Бэкап Alpine.js кода в `frontend-alpine/`
- Тестировать каждый этап перед переходом к следующему

---

## 📝 Шаблон запроса для нового чата

```
Добрый день! Продолжаем работу над проектом fedoc. 

Создана ветка `feature/vue-migration` для миграции Graph Viewer 
с Alpine.js на Vue.js 3. 

План миграции готов в `docs/decisions/vue-migration-plan.md` (7 этапов, 7-11 часов).

Контекст в `docs/decisions/NEW_CHAT_CONTEXT.md`.

Начинаем с Этапа 1: настройка Vue.js проекта.

Текущая директория: `/home/alex/projects/rules/fedoc`
API сервер работает на порту 8899.

Готовы приступить к Этапу 1?
```

---

**Удачи в миграции!** 🚀

