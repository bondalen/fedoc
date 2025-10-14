# Установка и использование fedoc

Инструкция по установке проекта fedoc на новой машине и использованию инструмента визуализации графов.

---

## 📦 Быстрая установка

### 1️⃣ Клонировать репозиторий

```bash
git clone https://github.com/bondalen/fedoc.git
cd fedoc
```

### 2️⃣ Установить зависимости

```bash
pip install -r requirements.txt
```

**Устанавливаемые зависимости:**
- `python-arango>=7.5.0` - для подключения к ArangoDB
- `pyvis>=0.3.2` - для визуализации графов
- `networkx>=3.1` - для работы с графами
- `pydantic>=2.0.0` - для валидации данных
- `python-dotenv>=1.0.0` - для работы с переменными окружения

### 3️⃣ Настроить доступ к ArangoDB

#### Вариант А: ArangoDB на локальной машине

Если ArangoDB запущен локально на порту 8529:

```bash
# Просто запустить визуализацию
dev/tools/view-graph.sh
```

#### Вариант Б: ArangoDB на удалённом сервере (основной сценарий)

Если ArangoDB на сервере 176.108.244.252:

```bash
# 1. Создать SSH туннель
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N &

# 2. Запустить визуализацию
dev/tools/view-graph.sh --project fepro
```

**Примечание:** SSH туннель перенаправляет удалённый порт 8529 на локальный localhost:8529

---

## 🎨 Использование визуализации графов

### Базовые команды

```bash
# Визуализировать весь граф всех проектов
dev/tools/view-graph.sh

# Визуализировать только проект FEPRO
dev/tools/view-graph.sh --project fepro

# Визуализировать только проект FEMSQ
dev/tools/view-graph.sh --project femsq

# Визуализировать только проект fedoc
dev/tools/view-graph.sh --project fedoc
```

### Расширенные параметры

```bash
# Изменить глубину обхода графа
dev/tools/view-graph.sh --project fepro --depth 8

# Изменить тему оформления
dev/tools/view-graph.sh --project femsq --theme light

# Указать стартовую вершину
dev/tools/view-graph.sh --start-node "canonical_nodes/t:java@21" --depth 5

# Не открывать браузер автоматически
dev/tools/view-graph.sh --project fepro --no-browser

# Указать выходной файл
dev/tools/view-graph.sh --output /tmp/my-graph.html
```

### Все доступные параметры

| Параметр | Описание | Значение по умолчанию |
|----------|----------|----------------------|
| `--project` | Фильтр по проекту (fepro, femsq, fedoc) | Все проекты |
| `--start-node` | Стартовая вершина для обхода | `canonical_nodes/c:backend` |
| `--depth` | Глубина обхода (количество рёбер) | 10 |
| `--theme` | Тема оформления (dark/light) | dark |
| `--output` | Путь к выходному HTML файлу | `/tmp/arango-graph.html` |
| `--no-browser` | Не открывать браузер автоматически | false |
| `--max-nodes` | Максимальное количество узлов | 1000 |

---

## ⚙️ Настройка пароля ArangoDB

Пароль по умолчанию жёстко прописан в скрипте для удобства. Если нужно изменить:

### Способ 1: Через переменную окружения (рекомендуется)

```bash
export ARANGO_PASSWORD="ваш_пароль"
dev/tools/view-graph.sh
```

### Способ 2: Напрямую в команде

```bash
ARANGO_PASSWORD="ваш_пароль" dev/tools/view-graph.sh --project fepro
```

### Способ 3: Передать явно через Python

```bash
cd src
python3 -m lib.graph_viewer.viewer \
    --password "ваш_пароль" \
    --project fepro
```

### Способ 4: Создать файл .env

```bash
# Создать файл .env в корне проекта
echo "ARANGO_PASSWORD=ваш_пароль" > .env

# Скрипт автоматически подхватит пароль
dev/tools/view-graph.sh
```

---

## 🔧 Требования к системе

### Минимальные требования

- **Python:** 3.10 или новее
- **ОС:** Linux, macOS, Windows (с WSL или Git Bash)
- **Память:** 512 MB RAM (для визуализации)
- **Браузер:** Любой современный (Chrome, Firefox, Safari, Edge)

### Доступ к ArangoDB

Один из вариантов:
- ArangoDB на localhost:8529, или
- SSH доступ к серверу с ArangoDB, или
- Прямой сетевой доступ к ArangoDB

### Проверка версии Python

```bash
python3 --version
# Должно быть: Python 3.10.x или выше
```

---

## ✅ Проверка работоспособности

### Шаг 1: Проверить права на скрипт

```bash
ls -la dev/tools/view-graph.sh
```

Если нет прав на выполнение:

```bash
chmod +x dev/tools/view-graph.sh
```

### Шаг 2: Проверить импорт библиотеки

```bash
python3 -c "import sys; sys.path.insert(0, 'src'); from lib.graph_viewer import ArangoGraphViewer; print('✅ Библиотека graph_viewer работает')"
```

### Шаг 3: Проверить подключение к ArangoDB

```bash
# Через SSH туннель
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N &

# Проверить доступность
curl -s http://localhost:8529/_api/version | python3 -m json.tool
```

Должен вернуться JSON с версией ArangoDB.

### Шаг 4: Запустить тестовую визуализацию

```bash
dev/tools/view-graph.sh --project fedoc --depth 3
```

Должен открыться браузер с интерактивным графом.

---

## 🎛️ Интерактивная панель управления

После открытия графа в браузере доступна панель управления:

### Элементы панели

1. **Стартовая вершина** - выбор узла, от которого строить граф
2. **Глубина обхода** - слайдер от 1 до 15 рёбер
3. **Проект** - фильтр по проекту (все/fepro/femsq/fedoc)
4. **Тема** - переключение между тёмной и светлой темой
5. **Кнопка "Обновить"** - перезагрузить граф с новыми параметрами
6. **Кнопка "Подогнать"** - автоматически подогнать размер графа
7. **Счётчики** - количество узлов и рёбер в реальном времени

### Интерактивные возможности

- **Масштабирование:** колесо мыши
- **Перемещение:** перетаскивание мышью
- **Информация о узле:** наведение курсора
- **Навигация:** встроенные кнопки навигации
- **Поиск:** встроенный поиск по узлам

---

## 🐛 Устранение неполадок

### Проблема: "Connection refused"

**Причина:** SSH туннель не создан или ArangoDB недоступен

**Решение:**
```bash
# Проверить SSH туннель
ps aux | grep "ssh.*8529"

# Создать туннель заново
ssh -L 8529:localhost:8529 user1@176.108.244.252 -N &
```

### Проблема: "Authentication failed"

**Причина:** Неверный пароль ArangoDB

**Решение:**
```bash
# Передать правильный пароль
ARANGO_PASSWORD="правильный_пароль" dev/tools/view-graph.sh
```

### Проблема: "ModuleNotFoundError: No module named 'arango'"

**Причина:** Не установлены зависимости

**Решение:**
```bash
pip install -r requirements.txt
```

### Проблема: "Permission denied: ./view-graph.sh"

**Причина:** Нет прав на выполнение скрипта

**Решение:**
```bash
chmod +x dev/tools/view-graph.sh
```

### Проблема: Граф не отображается в браузере

**Причина:** Граф пуст или не найден

**Решение:**
```bash
# Проверить, что граф существует в ArangoDB
curl -u root:пароль http://localhost:8529/_api/database/fedoc

# Проверить наличие данных
python3 -c "
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('fedoc', username='root', password='пароль')
print('Коллекции:', db.collections())
"
```

---

## 📚 Дополнительные ресурсы

### Документация проекта

- [Структура проекта](../README.md)
- [Архитектурные решения](../docs/project/decisions/)
- [История разработки](project-history/)
- [Концепция системы](concepts/centralized-documentation-system-concept.md)

### Документация компонентов

- [Библиотека graph_viewer](../src/lib/graph_viewer/README.md)
- [MCP-сервер](../src/mcp_server/README.md)
- [Docker конфигурация](../dev/docker/README.md)

### Внешние ресурсы

- [ArangoDB Documentation](https://www.arangodb.com/docs/)
- [PyVis Documentation](https://pyvis.readthedocs.io/)
- [NetworkX Documentation](https://networkx.org/)

---

## 🆘 Получение помощи

Если возникли проблемы:

1. Проверьте раздел "Устранение неполадок" выше
2. Проверьте логи: `python3 -m lib.graph_viewer.viewer --help`
3. Создайте issue в репозитории: https://github.com/bondalen/fedoc/issues

---

**Дата создания:** 2025-10-14  
**Версия:** 1.0  
**Статус:** ✅ Актуально
