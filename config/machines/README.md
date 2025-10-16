# Профили машин для Graph Viewer

Эта директория содержит профили конфигурации для разных машин (рабочих станций, ноутбуков и т.д.).

## Формат имени файла

```
{username}-{hostname}.yaml
```

Примеры:
- `alex-fedora.yaml` - рабочая машина
- `alex-laptop.yaml` - ноутбук
- `john-ubuntu.yaml` - машина коллеги

## Автоопределение

При запуске Graph Viewer система автоматически определяет текущую машину по `${USER}-${HOSTNAME}` и ищет соответствующий профиль.

## Создание профиля для новой машины

### Автоматически (рекомендуется)

Просто запустите Graph Viewer через MCP:
```
"Открой graph viewer"
```

Если профиль не найден, система:
1. Спросит параметры у пользователя
2. Создаст профиль с разумными defaults
3. Сохранит его в `config/machines/{user}-{hostname}.yaml`
4. Предложит закоммитить (для общего доступа)

### Вручную

Скопируйте существующий профиль и отредактируйте:

```bash
cp alex-fedora.yaml john-ubuntu.yaml
# Отредактируйте параметры
```

## Структура профиля

```yaml
# Информация о машине
machine:
  hostname: "fedora"           # hostname без домена
  username: "alex"             # имя пользователя
  os: "linux"                  # linux, darwin, windows
  description: "..."           # описание

# SSH настройки
ssh:
  key_path: "~/.ssh/id_ed25519"
  config_path: "~/.ssh/config"

# Пути к инструментам
tools:
  python: "/usr/bin/python3"
  node: "/usr/bin/node"
  npm: "/usr/bin/npm"

# Пути проекта
project:
  root: "/home/alex/projects/rules/fedoc"
  venv: "/home/alex/projects/rules/fedoc/venv"

# Опции для этой машины
options:
  auto_open_browser: true
  verbose_logging: false
```

## Переопределение параметров

Параметры из профиля машины переопределяют базовую конфигурацию (`config/graph_viewer.yaml`).

Порядок приоритета (от низкого к высокому):
1. `config/graph_viewer.yaml` - базовая конфигурация
2. `config/machines/{user}-{hostname}.yaml` - профиль машины
3. `config/graph_viewer.local.yaml` - локальные переопределения (не в git)
4. Переменные окружения - финальное переопределение

## Коммит профилей в git

**Рекомендуется:** Профили машин коммитятся в git для:
- Легкой настройки новой машины
- Документирования окружений команды
- Переиспользования настроек между проектами

**НЕ коммитятся:**
- `config/graph_viewer.local.yaml` - личные настройки
- `config/.secrets.env` - пароли и секреты

## Примеры использования

### Разработка на нескольких машинах

```yaml
# alex-workstation.yaml - рабочая станция
options:
  auto_open_browser: true
  verbose_logging: true

# alex-laptop.yaml - ноутбук
ports:
  api_server: 9000  # Другой порт, если 8899 занят
options:
  auto_open_browser: false  # Ручной запуск браузера
```

### CI/CD окружение

```yaml
# ci-runner.yaml - CI сервер
machine:
  hostname: "ci-runner"
  username: "gitlab-runner"
  
options:
  auto_open_browser: false  # Нет дисплея
  auto_install_npm: true    # Автоустановка зависимостей
  
environment:
  display: null  # Headless окружение
```

## Полезные команды

```bash
# Узнать имя профиля для текущей машины
echo "$(whoami)-$(hostname -s)"

# Проверить существует ли профиль
ls config/machines/$(whoami)-$(hostname -s).yaml

# Создать профиль вручную
cat > config/machines/$(whoami)-$(hostname -s).yaml << EOF
machine:
  hostname: "$(hostname -s)"
  username: "$(whoami)"
  os: "$(uname -s | tr '[:upper:]' '[:lower:]')"
EOF
```



