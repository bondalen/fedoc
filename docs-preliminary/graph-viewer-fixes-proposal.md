# Предложения по исправлениям Graph Viewer для работы через MCP

**Дата:** 2025-10-20  
**Статус:** Предложение (не реализовано)  
**Цель:** Обеспечить корректный запуск Graph Viewer через MCP команду `open_graph_viewer` на разных машинах

---

## 🎯 Обнаруженные проблемы

### 1. **SSH туннель только для ArangoDB (устаревший)**
**Файл:** `src/lib/graph_viewer/backend/tunnel_manager.py`  
**Проблема:** Создается туннель только на порт 8529 (ArangoDB), но после миграции нужен туннель на порт 5432 (PostgreSQL)

**Текущий код:**
```python
self.local_port = config.get('ports.ssh_tunnel', 8529)
self.remote_port = config.get('ports.ssh_tunnel', 8529)
```

**Эффект:** API сервер не может подключиться к PostgreSQL через SSH туннель

---

### 2. **Хардкод портов в конфигурации**
**Файл:** `config/graph_viewer.yaml`  
**Проблема:** Устаревшие порты для ArangoDB, нет настроек для PostgreSQL

**Текущая конфигурация:**
```yaml
ports:
  ssh_tunnel: 8529      # ArangoDB (устарело)
  api_server: 8899      # Неправильный порт
  vite_server: 5173     # OK
```

**Эффект:** Неправильные порты для PostgreSQL setup

---

### 3. **ProcessManager ищет неправильный скрипт**
**Файл:** `src/lib/graph_viewer/backend/process_manager.py:114`  
**Проблема:** Ищет процесс по паттерну `api_server.py`, но реальный файл `api_server_age.py`

**Текущий код:**
```python
def check_api_server(self) -> Optional[int]:
    return self._find_process(r"python.*api_server\.py")
```

**Эффект:** MCP не видит запущенный API сервер (показывает `stopped`)

---

### 4. **Vite конфигурация с неправильными портами**
**Файл:** `src/lib/graph_viewer/frontend/vite.config.js`  
**Проблема:** Proxy настроен на порт 8899 вместо 15000 (уже исправлено вручную)

**Было:**
```javascript
proxy: {
  '/api': { target: 'http://127.0.0.1:8899', ... },
  '/socket.io': { target: 'ws://127.0.0.1:8899', ... }
}
```

**Стало (временное исправление):**
```javascript
proxy: {
  '/api': { target: 'http://127.0.0.1:15000', ... },
  '/socket.io': { target: 'ws://127.0.0.1:15000', ... }
}
```

**Эффект:** Фронтенд не может подключиться к API серверу

---

### 5. **WebSocket с хардкод портом**
**Файл:** `src/lib/graph_viewer/frontend/src/stores/graph.js:606`  
**Проблема:** WebSocket подключается к `http://localhost:8899` напрямую (уже исправлено вручную)

**Было:**
```javascript
socket = io('http://localhost:8899', { ... })
```

**Стало (временное исправление):**
```javascript
socket = io({ ... })  // Использует Vite proxy
```

**Эффект:** WebSocket не работает без явного указания порта

---

### 6. **Отсутствие конфигурации для PostgreSQL**
**Проблема:** Нет настроек для PostgreSQL туннеля и подключения в конфигурации

**Что отсутствует:**
- Параметры PostgreSQL туннеля (local_port, remote_port)
- Параметры подключения к PostgreSQL (host, port, database, user)
- Пароль PostgreSQL в конфигурации или env

---

## ✅ Предложения по исправлениям

### **Исправление 1: Расширить TunnelManager для нескольких туннелей**

**Файл:** `src/lib/graph_viewer/backend/tunnel_manager.py`

**Подход:** Создать универсальный класс для управления несколькими туннелями

```python
class TunnelManager:
    """Менеджер SSH туннелей (поддержка нескольких туннелей)"""
    
    def __init__(self, config: Optional['ConfigManager'] = None):
        self.config = config
        self.tunnels = {}  # Словарь активных туннелей
        
        if config:
            # Загружаем конфигурацию туннелей
            self.remote_host = config.get('remote_server.ssh_alias', 'fedoc-server')
            
            # PostgreSQL туннель
            self.tunnels['postgres'] = {
                'local_port': config.get('ports.postgres_tunnel', 15432),
                'remote_port': config.get('postgres.port', 5432),
                'name': 'PostgreSQL',
                'pid': None
            }
            
            # ArangoDB туннель (legacy, опционально)
            if config.get('arango.enabled', False):
                self.tunnels['arango'] = {
                    'local_port': config.get('ports.arango_tunnel', 8529),
                    'remote_port': config.get('arango.port', 8529),
                    'name': 'ArangoDB',
                    'pid': None
                }
    
    def check_tunnel(self, tunnel_name: str) -> Optional[int]:
        """Проверить конкретный туннель"""
        if tunnel_name not in self.tunnels:
            return None
        
        tunnel = self.tunnels[tunnel_name]
        # ... существующая логика поиска процесса ...
        pattern = rf"ssh.*-L\s+{tunnel['local_port']}:localhost:{tunnel['remote_port']}.*{self.remote_host}"
        # ... вернуть PID или None
    
    def create_tunnel(self, tunnel_name: str) -> bool:
        """Создать конкретный туннель"""
        # ... логика создания ...
    
    def ensure_all_tunnels(self) -> bool:
        """Создать все настроенные туннели"""
        success = True
        for name in self.tunnels.keys():
            if not self.check_tunnel(name):
                if not self.create_tunnel(name):
                    success = False
        return success
    
    def get_status(self) -> Dict[str, any]:
        """Статус всех туннелей"""
        status = {}
        for name, tunnel in self.tunnels.items():
            pid = self.check_tunnel(name)
            status[name] = {
                'name': tunnel['name'],
                'local_port': tunnel['local_port'],
                'remote_port': tunnel['remote_port'],
                'status': 'connected' if pid else 'disconnected',
                'pid': pid
            }
        return status
```

**Преимущества:**
- ✅ Поддержка нескольких туннелей (PostgreSQL + ArangoDB)
- ✅ Легко добавлять новые туннели
- ✅ Централизованное управление

---

### **Исправление 2: Обновить конфигурацию для PostgreSQL**

**Файл:** `config/graph_viewer.yaml`

```yaml
# Конфигурация Graph Viewer для fedoc
version: "2.0"  # Увеличиваем версию

# Удаленный сервер
remote_server:
  host: "176.108.244.252"
  user: "user1"
  ssh_alias: "fedoc-server"
  description: "Production сервер с PostgreSQL + Apache AGE"

# Порты
ports:
  # SSH туннели
  postgres_tunnel: 15432    # Локальный порт для PostgreSQL туннеля
  arango_tunnel: 8529       # Локальный порт для ArangoDB туннеля (legacy)
  
  # Сервисы
  api_server: 15000         # REST API для графов (исправлено с 8899)
  vite_server: 5173         # Vue.js dev сервер

# PostgreSQL настройки (основная БД)
postgres:
  enabled: true
  port: 5432                # Порт на удаленном сервере
  host: "localhost"         # Через SSH туннель
  database: "fedoc"
  user: "postgres"
  password_env: "POSTGRES_PASSWORD"  # Переменная окружения
  default_password: "fedoc_test_2025"  # Пароль по умолчанию

# ArangoDB настройки (legacy, только для миграции)
arango:
  enabled: false            # Отключено после миграции
  port: 8529
  host: "http://localhost:8529"
  database: "fedoc"
  user: "root"
  password_env: "ARANGO_PASSWORD"

# Пути относительно корня проекта
paths:
  frontend: "src/lib/graph_viewer/frontend"
  backend: "src/lib/graph_viewer/backend"
  venv_python: "venv/bin/python"

# Логи
logs:
  api_server: "/tmp/graph_viewer_api.log"
  vite_server: "/tmp/graph_viewer_vite.log"
  level: "INFO"

# Опции по умолчанию
options:
  auto_install_npm: false
  auto_create_ssh_config: true
  auto_create_ssh_key: false
  check_dependencies: true
  timeout_seconds: 30
  auto_open_browser: true

# Профили машин
machines:
  enabled: true
  auto_detect: true
  ask_if_unknown: true
  directory: "config/machines"
  save_new_profiles: true
```

**Изменения:**
- ✅ Добавлена секция `postgres` с настройками подключения
- ✅ Разделены порты туннелей: `postgres_tunnel` и `arango_tunnel`
- ✅ Исправлен порт API сервера: 8899 → 15000
- ✅ ArangoDB помечен как legacy (`enabled: false`)

---

### **Исправление 3: Исправить ProcessManager**

**Файл:** `src/lib/graph_viewer/backend/process_manager.py`

**3.1. Исправить check_api_server() - строка 114:**
```python
def check_api_server(self) -> Optional[int]:
    """Проверить работает ли API сервер"""
    # БЫЛО: return self._find_process(r"python.*api_server\.py")
    # СТАЛО:
    return self._find_process(r"python.*api_server_age\.py")
```

**3.2. Использовать правильный порт из конфигурации - строка 58:**
```python
# БЫЛО:
self.api_port = config.get('ports.api_server', 8899)

# СТАЛО:
self.api_port = config.get('ports.api_server', 15000)
```

**3.3. Использовать параметры PostgreSQL из конфигурации - строка 148:**
```python
# БЫЛО (хардкод):
subprocess.Popen([
    str(self.venv_python),
    str(api_script),
    "--db-host", "localhost",
    "--db-port", "15432",  # Хардкод!
    "--db-name", "fedoc",
    "--db-user", "postgres",
    "--db-password", self.arango_password
], ...)

# СТАЛО (из конфигурации):
pg_config = self.config if self.config else {}
subprocess.Popen([
    str(self.venv_python),
    str(api_script),
    "--port", str(self.api_port),
    "--db-host", pg_config.get('postgres.host', 'localhost'),
    "--db-port", str(pg_config.get('ports.postgres_tunnel', 15432)),
    "--db-name", pg_config.get('postgres.database', 'fedoc'),
    "--db-user", pg_config.get('postgres.user', 'postgres'),
    "--db-password", pg_config.get('postgres.default_password', 'fedoc_test_2025')
], ...)
```

**Преимущества:**
- ✅ Корректно находит процесс API сервера
- ✅ Использует правильный порт API
- ✅ Гибкая конфигурация через config файлы

---

### **Исправление 4: Динамическая конфигурация Vite через ConfigManager**

**Проблема:** Vite конфигурация статична и не может читать порты из config файлов

**Решение 1 (рекомендуется): Использовать переменные окружения**

**Файл:** `src/lib/graph_viewer/frontend/vite.config.js`
```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Читаем порт API сервера из переменной окружения
const API_PORT = process.env.VITE_API_PORT || '15000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
      '/socket.io': {
        target: `ws://127.0.0.1:${API_PORT}`,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
```

**Изменения в ProcessManager.start_vite_server() - строка 200:**
```python
def start_vite_server(self) -> bool:
    # ...
    env = os.environ.copy()
    env['VITE_API_PORT'] = str(self.api_port)  # Передаем порт через env
    
    subprocess.Popen(
        ["npm", "run", "dev"],
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=self.frontend_dir,
        env=env,  # Передаем environment с VITE_API_PORT
        start_new_session=True
    )
```

**Решение 2 (альтернатива): Генерировать vite.config.js динамически**

Не рекомендуется, т.к. усложняет разработку.

---

### **Исправление 5: Убрать хардкод из WebSocket инициализации**

**Файл:** `src/lib/graph_viewer/frontend/src/stores/graph.js:606`

**Уже исправлено вручную**, но нужно закоммитить:
```javascript
// БЫЛО:
socket = io('http://localhost:8899', { ... })

// СТАЛО (правильно):
socket = io({  // Без URL - использует текущий хост через Vite proxy
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
})
```

**Статус:** ✅ Уже исправлено, нужно только закоммитить

---

### **Исправление 6: Обновить graph_viewer_manager для создания PostgreSQL туннеля**

**Файл:** `src/mcp_server/handlers/graph_viewer_manager.py`

**Изменения в open_graph_viewer() - строка 102:**
```python
def open_graph_viewer(...):
    # ...
    tunnel_mgr = TunnelManager(config=config)
    
    # 1. Создаем все необходимые SSH туннели
    log("\n🔌 Проверка SSH туннелей...")
    
    # БЫЛО:
    # tunnel_ok = tunnel_mgr.ensure_tunnel()
    
    # СТАЛО:
    tunnel_ok = tunnel_mgr.ensure_all_tunnels()  # Создает все туннели из конфига
    
    if not tunnel_ok:
        return {
            "status": "error",
            "message": "Не удалось создать SSH туннели",
            "details": "Проверьте SSH доступ и конфигурацию туннелей"
        }
    
    # Получаем статус всех туннелей
    tunnels_status = tunnel_mgr.get_status()
    results["components"]["ssh_tunnels"] = tunnels_status
    
    # Проверяем что PostgreSQL туннель активен
    if 'postgres' in tunnels_status and tunnels_status['postgres']['status'] == 'connected':
        log(f"   ✓ PostgreSQL туннель активен (порт {tunnels_status['postgres']['local_port']})")
    else:
        log("   ⚠️ PostgreSQL туннель не активен")
    
    # ... остальной код ...
```

---

### **Исправление 7: Обновить профили машин**

**Файл:** `config/machines/alex-User-PC.yaml` (новый файл для WSL)

```yaml
# Профиль машины: alex-User-PC (Windows WSL2)
machine:
  hostname: "User-PC"
  username: "alex"
  os: "WSL2"
  distribution: "Ubuntu 24.04"
  description: "Windows с WSL2"
  added: "2025-10-20"

# SSH настройки
ssh:
  key_path: "~/.ssh/id_ed25519"
  config_path: "~/.ssh/config"

# Пути к инструментам
tools:
  python: "/usr/bin/python3"
  node: "/usr/bin/node"
  npm: "/usr/bin/npm"

# Пути проекта (абсолютные)
project:
  root: "/home/alex/fedoc"
  venv: "/home/alex/fedoc/venv"

# Особенности окружения
environment:
  shell: "/bin/bash"
  # В WSL нужно открывать браузер через cmd.exe
  browser_command: "cd /mnt/c && cmd.exe /c start"
  
# Опции для этой машины
options:
  auto_open_browser: true
  verbose_logging: false

# Примечания
# - Браузер открывается через cmd.exe
# - SSH туннели работают нормально
# - npm зависимости установлены
```

**Изменения в graph_viewer_manager.py для WSL:**
```python
def open_graph_viewer(...):
    # ...
    # 5. Открываем браузер с учетом WSL
    browser_setting = config.get('options.auto_open_browser', True)
    if auto_open_browser and browser_setting:
        log(f"\n🌐 Открываю браузер: {url}")
        
        # Проверяем WSL
        browser_cmd = config.get('environment.browser_command')
        if browser_cmd:
            # WSL: используем специальную команду
            import subprocess
            subprocess.run(f'{browser_cmd} {url}', shell=True)
        else:
            # Обычная система
            webbrowser.open(url)
        
        results["browser_opened"] = True
```

---

## 📋 План реализации

### Фаза 1: Конфигурация (приоритет 1)
1. ✅ Обновить `config/graph_viewer.yaml` - добавить PostgreSQL настройки
2. ✅ Создать профиль `config/machines/alex-User-PC.yaml` для WSL
3. ✅ Обновить `.gitignore` чтобы не коммитить пароли

### Фаза 2: Tunnel Manager (приоритет 1)
4. ✅ Расширить `TunnelManager` для поддержки нескольких туннелей
5. ✅ Добавить метод `ensure_all_tunnels()`
6. ✅ Обновить `get_status()` для всех туннелей

### Фаза 3: Process Manager (приоритет 1)
7. ✅ Исправить `check_api_server()` - искать `api_server_age.py`
8. ✅ Использовать порты из конфигурации вместо хардкода
9. ✅ Передавать `VITE_API_PORT` через environment

### Фаза 4: Frontend (приоритет 2)
10. ✅ Обновить `vite.config.js` для использования `process.env.VITE_API_PORT`
11. ✅ Убедиться что `graph.js` использует относительный путь для WebSocket (уже сделано)

### Фаза 5: MCP Handler (приоритет 2)
12. ✅ Обновить `graph_viewer_manager.py` для создания всех туннелей
13. ✅ Добавить поддержку WSL в открытии браузера

### Фаза 6: Тестирование (приоритет 3)
14. ✅ Тестировать на WSL (alex-User-PC)
15. ✅ Тестировать на Fedora (alex-fedora)
16. ✅ Обновить документацию

---

## 🎯 Критерии успеха

После реализации исправлений:

### ✅ На любой машине из config:
```bash
# В Cursor AI:
"Открой граф вьювер"
```

**Ожидаемый результат:**
1. ✅ Автоопределение машины (alex-User-PC, alex-fedora, etc.)
2. ✅ Создание SSH туннелей для PostgreSQL (и ArangoDB если enabled)
3. ✅ Запуск API сервера на правильном порту (15000)
4. ✅ Запуск Vite сервера с правильным proxy
5. ✅ Открытие браузера (с учетом WSL/Linux/macOS)
6. ✅ Загрузка графа (39 узлов, 34 ребра)
7. ✅ Работающий WebSocket

### ✅ MCP status команда показывает правильный статус:
```bash
"Проверь статус graph viewer"
```

**Ожидаемый вывод:**
```
✅ Общий статус: running
🖥️  Машина: alex-User-PC

🔧 Компоненты:
   ✅ postgres_tunnel: connected (PID: 2929)
   ✅ api_server: running (PID: 2990)
   ✅ vite_server: running (PID: 3080)

🌐 Интерфейс доступен: http://localhost:5173
```

---

## 🔄 Обратная совместимость

### Сохраняется:
- ✅ Старые профили машин работают
- ✅ Можно запускать вручную через CLI
- ✅ ArangoDB туннель опционален (для legacy доступа)

### Ломается:
- ❌ Старый порт API (8899) больше не используется
- ❌ Прямые вызовы `TunnelManager` без config могут не работать
  
### Миграция:
1. Обновить `config/graph_viewer.yaml` (один раз)
2. Создать профили машин (автоматически при первом запуске)
3. Перезапустить Graph Viewer через MCP

---

## 📝 Дополнительные улучшения (опционально)

### 1. Healthcheck для компонентов
Добавить проверку здоровья компонентов:
- HTTP запрос к API серверу
- Проверка WebSocket соединения
- Проверка доступности PostgreSQL через туннель

### 2. Auto-restart при падении
Автоматический перезапуск упавших компонентов:
- Мониторинг процессов
- Автоматический restart при сбое

### 3. Логирование в файлы
Централизованное логирование:
- Ротация логов
- Уровни логирования (DEBUG, INFO, WARNING, ERROR)
- Агрегация ошибок

---

## 🚀 Результат

После реализации всех исправлений:

**Одна команда в Cursor AI:**
```
"Открой граф вьювер"
```

**Работает на любой машине:**
- ✅ Windows WSL2 (alex-User-PC)
- ✅ Fedora 42 (alex-fedora)
- ✅ Любая другая машина из config/machines/

**Без ручных действий:**
- ✅ SSH туннели создаются автоматически
- ✅ API сервер запускается на правильном порту
- ✅ Vite настраивается динамически
- ✅ Браузер открывается корректно
- ✅ Граф загружается и работает

---

**Автор:** AI Assistant  
**Дата:** 2025-10-20  
**Статус:** Готово к реализации



