# Реестр модулей и компонентов multigraph

Документ фиксирует состав модулей, компонентов и классов системы multigraph. Нумерация `X.Y.Z.*` поддерживает произвольную (по сути бесконечную) вложенность, поэтому реестр может содержать все классы, а не только ключевые. Для каждого элемента указывается тип (`Module`, `Component`, `Class`), текущий статус разработки и ссылки на резюме чатов.

Правила вложенности:
- Модуль (`Module`) может включать подмодули, компоненты и классы.
- Компонент (`Component`) может включать компоненты и классы, но **не** подмодули.
- Класс (`Class`) является листом и не содержит вложенных элементов.

Обозначения статусов:
- `planned` — задача запланирована;
- `in progress` — работа ведётся;
- `done` — реализовано (ссылка на чат обязательна);
- `n/a` — не требуется / внешняя зависимость.

> При завершении работы над элементом обновляйте статус и добавляйте ссылку на соответствующее резюме чата (`docs/multigraph/bb-chats`). Если внутри модуля/компонента появляются новые классы, расширяйте нумерацию вниз (например, `1.1.2.1`, `1.1.2.1.1`).

---

## 1. Backend (mgsrc/backend) — *Module*
- Статус: `in progress`
- Задачи: bb-tasks 1.*
- ФС:  mgsrc/backend

### 1.1 API Gateway / Flask Blueprint — *Component*
- Статус: `done`
- Задачи: bb-tasks 1.1.*
- Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)
- ФС:  mgsrc/backend/fedoc_multigraph
- **1.1.1 Application Factory (`fedoc_multigraph.app:create_app`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/app.py
- **1.1.2 Blueprint Registry (`fedoc_multigraph.app:register_blueprints`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/app.py
- **1.1.3 Routing Table (`fedoc_multigraph.urls`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/urls.py
- **1.1.4 Middleware Stack (`fedoc_multigraph.middleware`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/middleware
- **1.1.5 Error Handlers (`fedoc_multigraph.errors`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md), [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md), [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/errors
  - **1.1.5.1 BlockNotFoundError (`errors.blocks:BlockNotFoundError`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/errors/blocks.py
  - **1.1.5.2 BlockConflictError (`errors.blocks:BlockConflictError`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/errors/blocks.py
  - **1.1.5.3 DesignNotFoundError (`errors.designs:DesignNotFoundError`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/errors/designs.py
  - **1.1.5.4 DesignConflictError (`errors.designs:DesignConflictError`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/errors/designs.py
- **1.1.6 Validation Schemas (`fedoc_multigraph.validators`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md), [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/validators
  - **1.1.6.1 BlockCreateSchema (`validators.blocks:BlockCreateSchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/blocks.py
  - **1.1.6.2 BlockUpdateSchema (`validators.blocks:BlockUpdateSchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/blocks.py
  - **1.1.6.3 BlockQuerySchema (`validators.blocks:BlockQuerySchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/blocks.py
  - **1.1.6.4 DesignCreateSchema (`validators.designs:DesignCreateSchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/designs.py
  - **1.1.6.5 DesignUpdateSchema (`validators.designs:DesignUpdateSchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/designs.py
  - **1.1.6.6 DesignQuerySchema (`validators.designs:DesignQuerySchema`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/validators/designs.py
- **1.1.7 Auth Decorators (`fedoc_multigraph.auth`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/auth

### 1.2 REST Endpoints (`fedoc_multigraph/api`) — *Module*
- Задачи: bb-tasks 1.2.*
- ФС:  mgsrc/backend/fedoc_multigraph/api
- **1.2.1 Blocks API (`api.blocks`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.2.1  
  ФС:  mgsrc/backend/fedoc_multigraph/api/blocks.py
- **1.2.1.1 Blocks Blueprint (`api.blocks:blocks_bp`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.2.1
- **1.2.1.2 Block CRUD Endpoints (`api.blocks` view functions) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.2.1
- **1.2.2 Designs API (`api.designs`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.2.2  
  ФС:  mgsrc/backend/fedoc_multigraph/api/designs.py
- **1.2.2.1 Designs Blueprint (`api.designs:designs_bp`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.2.2
- **1.2.2.2 Design CRUD Endpoints (`api.designs` view functions) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.2.2
- **1.2.3 Projects API (`api.projects`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 1.2.3
- **1.2.4 Health Check (`api.health`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.2.4

### 1.3 Service Layer (`fedoc_multigraph/services`) — *Module*
- Задачи: bb-tasks 1.3.*
- ФС:  mgsrc/backend/fedoc_multigraph/services
- **1.3.1 Blocks Service (`services.blocks`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.3.1  
  ФС:  mgsrc/backend/fedoc_multigraph/services/blocks.py
- **1.3.1.1 BlocksService (`services.blocks:BlocksService`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: bb-tasks 1.3.1
- **1.3.2 Designs Service (`services.designs`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.3.1  
  ФС:  mgsrc/backend/fedoc_multigraph/services/designs.py
- **1.3.2.1 DesignsService (`services.designs:DesignsService`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
  Задачи: bb-tasks 1.3.1
- **1.3.3 Projects Aggregator (`services.projects`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 1.3.1
- **1.3.4 MCP Bridge (`handlers.mcp`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 1.3.1
- **1.3.5 WebSocket Hub (`ws.hub`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 1.3.1

### 1.4 Persistence & Infrastructure (`fedoc_multigraph/db`, `fedoc_multigraph/config`) — *Module*
- Задачи: *(уточнить в bb-tasks)*
- ФС:  mgsrc/backend/fedoc_multigraph
- **1.4.1 Config Provider (`config.settings`) — *Module***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1  
  ФС:  mgsrc/backend/fedoc_multigraph/config/settings.py
  - **1.4.1.1 Settings dataclass (`Settings`) — *Class***  
    Статус: `done`  
    Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
    Задачи: bb-tasks 1.1.1
- **1.4.2 DB Session Factory (`db.session`) — *Module***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: *(определить)*  
  ФС:  mgsrc/backend/fedoc_multigraph/db/session.py
- **1.4.3 Repository Adapter (`repositories.postgres`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
  Задачи: *(определить)*  
  ФС:  mgsrc/backend/fedoc_multigraph/db/repositories
- **1.4.3.1 BlocksRepository (`repositories.blocks:BlocksRepository`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-06-37.md](../bb-chats/chat-25-1109-resume-06-37.md), [chat-25-1109-resume-07-35.md](../bb-chats/chat-25-1109-resume-07-35.md)  
    Задачи: bb-tasks 1.2.1  
    ФС:  mgsrc/backend/fedoc_multigraph/db/repositories/blocks.py
- **1.4.3.2 DesignsRepository (`repositories.designs:DesignsRepository`) — *Class***  
  Статус: `done`  
  Чаты: [chat-25-1109-resume-09-45.md](../bb-chats/chat-25-1109-resume-09-45.md)  
    Задачи: bb-tasks 1.2.2  
    ФС:  mgsrc/backend/fedoc_multigraph/db/repositories/designs.py
- **1.4.4 Task Queue Integration (`infra.tasks`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: *(определить)*

---

## 2. Frontend (mgsrc/frontend) — *Module*
- Задачи: bb-tasks 2.*
- ФС:  mgsrc/frontend
- **2.1 SPA Core (`src/main.ts`, `App.vue`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 2.1.1
- **2.2 Graph Visualization (`src/modules/graph`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 2.2.1
- **2.3 API Client (`src/services/api.ts`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 2.1.2
- **2.4 UI Common Components (`src/components/common`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 2.2.3

---

## 3. MCP Client (mgsrc/mcp_client) — *Module*
- Задачи: bb-tasks 3.*
- ФС:  mgsrc/mcp_client
- **3.1 MCP Server Entry (`server.py`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 3.1.1
- **3.2 Command Handlers (`handlers/*.py`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 3.1.2
- **3.3 API Client (`api_client.py`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 3.1.2
- **3.4 WebSocket Client (`ws_client.py`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 3.2.1

---

## 4. Инфраструктура — *Module*
- Задачи: bb-tasks 4.*
- ФС:  mgsrc/backend
- **4.1 Docker Base Image (`docker/Dockerfile.base`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 4.1.1
- **4.2 Supervisor Config (`docker/supervisord.conf`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 4.1.1
- **4.3 Deployment Scripts (`deploy/*.sh`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 4.1.2
- **4.4 Packaging Setup (`mgsrc/backend/setup.py`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.1
- **4.5 Requirements Specification (`mgsrc/backend/requirements.txt`) — *Component***  
  Статус: `done`  
  Чаты: [chat-25-1108-resume-23-10.md](../bb-chats/chat-25-1108-resume-23-10.md)  
  Задачи: bb-tasks 1.1.2

---

## 5. Тесты и контроль качества — *Module*
- Задачи: bb-tasks 5.*
- ФС:  mgsrc/backend/tests
- **5.1 Backend Unit Tests (`tests/backend`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 5.1.1
- **5.2 Frontend Tests (`tests/frontend`) — *Component***  
  Статус: `planned`  
  Чаты: *(нет)*  
  Задачи: bb-tasks 5.1.1
- **5.3 Integration / Smoke Tests (`tests/integration`) — *Component***  
  Статус: `in progress`  
  Чаты: [chat-25-1109-resume-08-10.md](../bb-chats/chat-25-1109-resume-08-10.md)  
  Задачи: bb-tasks 5.2.1

---

*Последнее обновление: 2025-11-09*