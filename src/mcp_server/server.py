#!/usr/bin/env python3
"""
Fedoc MCP Server - сервер для управления Graph Viewer
Интеграция: ArangoDB + SSH туннели + Process Manager (API + Vite)

Версия 2.0 с поддержкой ConfigManager
"""

import sys
import json
import os
from pathlib import Path

# Добавляем путь к библиотекам
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импортируем обработчики
from handlers import graph_viewer_manager
from handlers.edge_manager import create_edge_manager_handler

class FedocMCPServer:
    """MCP сервер для управления Graph Viewer"""
    
    def __init__(self):
        self.name = "fedoc"
        self.version = "2.0.0"  # Обновлена версия после интеграции ConfigManager
        self.tools = {}
        self.handlers = {}
        self.config = self._load_config()
        self.imports_status = self._check_imports()
        self.arango_connection = self._init_arango()
        self.ssh_tunnel = self._init_ssh_tunnel()
        self.process_manager = self._init_process_manager()
        self.edge_manager = create_edge_manager_handler()
        self._register_tools()
        self._register_handlers()
    
    def _load_config(self):
        """Загрузка конфигурации из переменных окружения"""
        return {
            "server": {
                "name": os.getenv("MCP_SERVER_NAME", "fedoc"),
                "version": os.getenv("MCP_SERVER_VERSION", "1.0.0")
            },
            "arango": {
                "host": os.getenv("ARANGO_HOST", "http://localhost:8529"),
                "database": os.getenv("ARANGO_DB", "fedoc"),
                "user": os.getenv("ARANGO_USER", "root"),
                "password": os.getenv("ARANGO_PASSWORD", "fedoc_dev_2025")
            },
            "ssh": {
                "remote_host": os.getenv("SSH_REMOTE_HOST", "vuege-server"),
                "local_port": int(os.getenv("SSH_LOCAL_PORT", "8529")),
                "remote_port": int(os.getenv("SSH_REMOTE_PORT", "8529"))
            },
            "graph_viewer": {
                "api_port": int(os.getenv("GRAPH_VIEWER_API_PORT", "8899")),
                "frontend_port": int(os.getenv("GRAPH_VIEWER_FRONTEND_PORT", "5173"))
            }
        }
    
    def _check_imports(self):
        """Проверка доступности импортов"""
        imports_status = {
            "basic": {
                "json": True,
                "os": True,
                "sys": True
            },
            "external": {
                "arango": False,
                "subprocess": True,
                "webbrowser": True,
                "pathlib": True
            },
            "graph_viewer": {
                "tunnel_manager": False,
                "process_manager": False
            }
        }
        
        # Проверяем ArangoDB
        try:
            import arango
            imports_status["external"]["arango"] = True
        except ImportError:
            imports_status["external"]["arango"] = False
        
        # Проверяем Graph Viewer модули
        try:
            from lib.graph_viewer.backend import TunnelManager
            imports_status["graph_viewer"]["tunnel_manager"] = True
        except ImportError:
            imports_status["graph_viewer"]["tunnel_manager"] = False
        
        try:
            from lib.graph_viewer.backend import ProcessManager
            imports_status["graph_viewer"]["process_manager"] = True
        except ImportError:
            imports_status["graph_viewer"]["process_manager"] = False
        
        return imports_status
    
    def _init_arango(self):
        """Инициализация ArangoDB подключения"""
        arango_config = {
            "status": "disconnected",
            "host": self.config["arango"]["host"],
            "database": self.config["arango"]["database"],
            "user": self.config["arango"]["user"],
            "connection": None,
            "message": "ArangoDB подключение не инициализировано"
        }
        
        if self.imports_status["external"]["arango"]:
            try:
                import arango
                
                client = arango.ArangoClient(hosts=self.config["arango"]["host"])
                
                try:
                    db = client.db(
                        self.config["arango"]["database"],
                        username=self.config["arango"]["user"],
                        password=self.config["arango"]["password"]
                    )
                    
                    db.properties()
                    
                    arango_config["status"] = "connected"
                    arango_config["connection"] = db
                    arango_config["message"] = "ArangoDB подключение успешно установлено"
                    
                except Exception as e:
                    arango_config["status"] = "error"
                    arango_config["message"] = f"Ошибка подключения к ArangoDB: {str(e)}"
                    
            except Exception as e:
                arango_config["status"] = "error"
                arango_config["message"] = f"Ошибка инициализации ArangoDB: {str(e)}"
        else:
            arango_config["status"] = "unavailable"
            arango_config["message"] = "Модуль arango недоступен"
        
        return arango_config
    
    def _init_ssh_tunnel(self):
        """Инициализация SSH туннеля"""
        tunnel_config = {
            "status": "disconnected",
            "remote_host": self.config["ssh"]["remote_host"],
            "local_port": self.config["ssh"]["local_port"],
            "remote_port": self.config["ssh"]["remote_port"],
            "pid": None,
            "manager": None,
            "message": "SSH туннель не инициализирован"
        }
        
        if self.imports_status["graph_viewer"]["tunnel_manager"]:
            try:
                from lib.graph_viewer.backend import TunnelManager
                
                tunnel_manager = TunnelManager(
                    remote_host=self.config["ssh"]["remote_host"],
                    local_port=self.config["ssh"]["local_port"],
                    remote_port=self.config["ssh"]["remote_port"]
                )
                
                tunnel_config["manager"] = tunnel_manager
                
                # Проверяем существующий туннель
                existing_pid = tunnel_manager.check_tunnel()
                if existing_pid:
                    tunnel_config["status"] = "connected"
                    tunnel_config["pid"] = existing_pid
                    tunnel_config["message"] = f"SSH туннель уже активен (PID: {existing_pid})"
                else:
                    tunnel_config["status"] = "disconnected"
                    tunnel_config["message"] = "SSH туннель не активен"
                
            except Exception as e:
                tunnel_config["status"] = "error"
                tunnel_config["message"] = f"Ошибка инициализации SSH туннеля: {str(e)}"
        else:
            tunnel_config["status"] = "unavailable"
            tunnel_config["message"] = "TunnelManager недоступен"
        
        return tunnel_config
    
    def _init_process_manager(self):
        """Инициализация Process Manager"""
        pm_config = {
            "status": "disconnected",
            "api_port": self.config["graph_viewer"]["api_port"],
            "frontend_port": self.config["graph_viewer"]["frontend_port"],
            "api_pid": None,
            "vite_pid": None,
            "manager": None,
            "message": "Process Manager не инициализирован"
        }
        
        if self.imports_status["graph_viewer"]["process_manager"]:
            try:
                from lib.graph_viewer.backend import ProcessManager
                
                process_manager = ProcessManager(
                    arango_password=self.config["arango"]["password"]
                )
                
                pm_config["manager"] = process_manager
                
                # Проверяем существующие процессы
                api_pid = process_manager.check_api_server()
                vite_pid = process_manager.check_vite_server()
                
                if api_pid and vite_pid:
                    pm_config["status"] = "running"
                    pm_config["api_pid"] = api_pid
                    pm_config["vite_pid"] = vite_pid
                    pm_config["message"] = f"API (PID: {api_pid}) и Vite (PID: {vite_pid}) запущены"
                elif api_pid:
                    pm_config["status"] = "partial"
                    pm_config["api_pid"] = api_pid
                    pm_config["message"] = f"API запущен (PID: {api_pid}), Vite не активен"
                elif vite_pid:
                    pm_config["status"] = "partial"
                    pm_config["vite_pid"] = vite_pid
                    pm_config["message"] = f"Vite запущен (PID: {vite_pid}), API не активен"
                else:
                    pm_config["status"] = "stopped"
                    pm_config["message"] = "API и Vite не запущены"
                
            except Exception as e:
                pm_config["status"] = "error"
                pm_config["message"] = f"Ошибка инициализации Process Manager: {str(e)}"
        else:
            pm_config["status"] = "unavailable"
            pm_config["message"] = "ProcessManager недоступен"
        
        return pm_config
    
    def _register_tools(self):
        """Регистрация инструментов"""
        self.tools = {
            "open_graph_viewer": {
                "name": "open_graph_viewer",
                "description": "Открыть систему визуализации графа в браузере. Автоматически создает SSH туннель, запускает API и Vite серверы, открывает браузер.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Фильтр по проекту: fepro, femsq, fedoc или пусто для всех проектов",
                            "enum": ["fepro", "femsq", "fedoc"]
                        },
                        "auto_open_browser": {
                            "type": "boolean",
                            "description": "Автоматически открыть браузер (по умолчанию true)",
                            "default": True
                        }
                    }
                }
            },
            "graph_viewer_status": {
                "name": "graph_viewer_status",
                "description": "Проверить статус системы визуализации графа",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "stop_graph_viewer": {
                "name": "stop_graph_viewer",
                "description": "Остановить систему визуализации графа",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "stop_tunnel": {
                            "type": "boolean",
                            "description": "Также закрыть SSH туннель (по умолчанию false)",
                            "default": False
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Принудительное завершение процессов (kill -9)",
                            "default": False
                        }
                    }
                }
            },
            "check_imports": {
                "name": "check_imports",
                "description": "Проверить статус импортов и зависимостей",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "check_stubs": {
                "name": "check_stubs",
                "description": "Проверить статус умных заглушек",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "test_arango": {
                "name": "test_arango",
                "description": "Протестировать ArangoDB подключение",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "test_ssh": {
                "name": "test_ssh",
                "description": "Протестировать SSH туннель",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "get_selected_nodes": {
                "name": "get_selected_nodes",
                "description": "Получить объекты, выбранные пользователем в Graph Viewer. Запрашивает у браузера текущую выборку узлов и рёбер через WebSocket.",
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            },
            "add_edge": {
                "name": "add_edge",
                "description": "Добавить новое ребро между узлами с автоматической проверкой уникальности. Предотвращает создание дублирующих связей в обоих направлениях (A→B и B→A).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "from_node": {
                            "type": "string",
                            "description": "ID исходного узла (например 'canonical_nodes/c:backend')"
                        },
                        "to_node": {
                            "type": "string",
                            "description": "ID целевого узла (например 'canonical_nodes/t:java@21')"
                        },
                        "relation_type": {
                            "type": "string",
                            "description": "Тип связи (по умолчанию 'related')",
                            "default": "related"
                        },
                        "projects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список проектов, использующих эту связь (например ['fepro', 'femsq'])"
                        }
                    },
                    "required": ["from_node", "to_node"]
                }
            },
            "update_edge": {
                "name": "update_edge",
                "description": "Обновить существующее ребро с проверкой уникальности. Можно изменить узлы, тип связи или список проектов.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "edge_id": {
                            "type": "string",
                            "description": "ID ребра (например 'project_relations/12345')"
                        },
                        "from_node": {
                            "type": "string",
                            "description": "Новый исходный узел (optional)"
                        },
                        "to_node": {
                            "type": "string",
                            "description": "Новый целевой узел (optional)"
                        },
                        "relation_type": {
                            "type": "string",
                            "description": "Новый тип связи (optional)"
                        },
                        "projects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Новый список проектов (optional)"
                        }
                    },
                    "required": ["edge_id"]
                }
            },
            "delete_edge": {
                "name": "delete_edge",
                "description": "Удалить ребро из графа.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "edge_id": {
                            "type": "string",
                            "description": "ID ребра для удаления (например 'project_relations/12345')"
                        }
                    },
                    "required": ["edge_id"]
                }
            },
            "check_edge_uniqueness": {
                "name": "check_edge_uniqueness",
                "description": "Проверить, является ли связь между узлами уникальной. Проверяет оба направления (A→B и B→A).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "from_node": {
                            "type": "string",
                            "description": "ID исходного узла"
                        },
                        "to_node": {
                            "type": "string",
                            "description": "ID целевого узла"
                        },
                        "exclude_edge_id": {
                            "type": "string",
                            "description": "ID ребра для исключения из проверки (optional)"
                        }
                    },
                    "required": ["from_node", "to_node"]
                }
            }
        }
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Используем обработчики из handlers/graph_viewer_manager.py
        self.handlers = {
            "open_graph_viewer": self._handle_open_graph_viewer_v2,
            "graph_viewer_status": self._handle_graph_viewer_status_v2,
            "stop_graph_viewer": self._handle_stop_graph_viewer_v2,
            "check_imports": self._handle_check_imports,
            "check_stubs": self._handle_check_stubs,
            "test_arango": self._handle_test_arango,
            "test_ssh": self._handle_test_ssh,
            "get_selected_nodes": self._handle_get_selected_nodes,
            "add_edge": self._handle_add_edge,
            "update_edge": self._handle_update_edge,
            "delete_edge": self._handle_delete_edge,
            "check_edge_uniqueness": self._handle_check_edge_uniqueness
        }
    
    def _handle_open_graph_viewer_v2(self, arguments: dict) -> dict:
        """Делегирование в новый обработчик с ConfigManager"""
        try:
            result = graph_viewer_manager.open_graph_viewer(
                project=arguments.get("project"),
                auto_open_browser=arguments.get("auto_open_browser", True)
            )
            
            # Форматируем результат для MCP
            if result.get("status") == "success":
                text = f"✅ {result['message']}\n\n"
                text += f"🌐 URL: {result['url']}\n\n"
                text += "🔧 Компоненты:\n"
                for name, status in result.get("components", {}).items():
                    text += f"   • {name}: {status}\n"
                return {"content": [{"type": "text", "text": text}]}
            else:
                text = f"❌ {result['message']}\n\n"
                if "details" in result:
                    text += f"Детали: {result['details']}"
                return {"content": [{"type": "text", "text": text}]}
                
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Ошибка: {e}"}]}
    
    def _handle_graph_viewer_status_v2(self, arguments: dict) -> dict:
        """Делегирование в новый обработчик статуса"""
        try:
            result = graph_viewer_manager.graph_viewer_status()
            
            if result.get("status") != "error":
                status_icon = "✅" if result["overall_status"] == "running" else "⚠️" if result["overall_status"] == "partial" else "❌"
                text = f"{status_icon} Статус: {result['overall_status']}\n\n"
                text += f"🖥️  Машина: {result.get('machine', 'N/A')}\n\n"
                text += "🔧 Компоненты:\n"
                for name, comp in result.get("components", {}).items():
                    comp_icon = "✅" if comp["status"] in ["connected", "running"] else "❌"
                    pid = f" (PID: {comp['pid']})" if comp.get("pid") else ""
                    text += f"   {comp_icon} {name}: {comp['status']}{pid}\n"
                
                if result.get("ready"):
                    text += f"\n🌐 URL: {result['url']}"
                
                return {"content": [{"type": "text", "text": text}]}
            else:
                return {"content": [{"type": "text", "text": f"❌ {result['message']}"}]}
                
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Ошибка: {e}"}]}
    
    def _handle_stop_graph_viewer_v2(self, arguments: dict) -> dict:
        """Делегирование в новый обработчик остановки"""
        try:
            result = graph_viewer_manager.stop_graph_viewer(
                stop_tunnel=arguments.get("stop_tunnel", False),
                force=arguments.get("force", False)
            )
            
            text = f"✅ {result['message']}\n"
            if result.get("stopped"):
                text += f"\nОстановлено: {', '.join(result['stopped'])}"
            
            return {"content": [{"type": "text", "text": text}]}
                
        except Exception as e:
            return {"content": [{"type": "text", "text": f"❌ Ошибка: {e}"}]}
    
    def _handle_open_graph_viewer(self, arguments: dict) -> dict:
        """Открыть Graph Viewer"""
        project = arguments.get("project", "")
        auto_open_browser = arguments.get("auto_open_browser", True)
        
        arango_status = self.arango_connection["status"]
        ssh_status = self.ssh_tunnel["status"]
        pm_status = self.process_manager["status"]
        
        status_text = f"🚀 Graph Viewer: Полная интеграция\n"
        status_text += f"📊 Проект: {project or 'все проекты'}\n"
        status_text += f"🌐 Авто-открытие браузера: {auto_open_browser}\n\n"
        status_text += f"🔧 Статус компонентов:\n"
        status_text += f"   🗄️  ArangoDB: {arango_status}\n"
        status_text += f"   🔌 SSH туннель: {ssh_status} (PID: {self.ssh_tunnel['pid'] or 'N/A'})\n"
        status_text += f"   🚀 API сервер: {pm_status} (PID: {self.process_manager['api_pid'] or 'N/A'})\n"
        status_text += f"   ⚡ Vite сервер: {pm_status} (PID: {self.process_manager['vite_pid'] or 'N/A'})\n\n"
        
        all_connected = (
            arango_status == "connected" and
            ssh_status == "connected" and
            pm_status in ["running", "partial"]
        )
        
        if all_connected:
            status_text += f"✅ Все компоненты интегрированы и работают!\n"
            status_text += f"🎉 Graph Viewer готов к использованию!"
        else:
            status_text += f"⚠️  Некоторые компоненты недоступны:\n"
            if arango_status != "connected":
                status_text += f"   - ArangoDB: {self.arango_connection['message']}\n"
            if ssh_status != "connected":
                status_text += f"   - SSH: {self.ssh_tunnel['message']}\n"
            if pm_status not in ["running", "partial"]:
                status_text += f"   - Process Manager: {self.process_manager['message']}\n"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_graph_viewer_status(self, arguments: dict) -> dict:
        """Проверить статус Graph Viewer"""
        arango_status = self.arango_connection["status"]
        ssh_status = self.ssh_tunnel["status"]
        pm_status = self.process_manager["status"]
        
        status_text = f"📊 Graph Viewer Status: Полная интеграция\n"
        status_text += f"🔧 Компоненты:\n"
        status_text += f"   🗄️  ArangoDB: {arango_status} → {self.arango_connection['host']}/{self.arango_connection['database']}\n"
        status_text += f"   🔌 SSH туннель: {ssh_status} → {self.ssh_tunnel['remote_host']}:{self.ssh_tunnel['local_port']} (PID: {self.ssh_tunnel['pid'] or 'N/A'})\n"
        status_text += f"   🚀 API сервер: {pm_status} → localhost:{self.process_manager['api_port']} (PID: {self.process_manager['api_pid'] or 'N/A'})\n"
        status_text += f"   ⚡ Vite сервер: {pm_status} → localhost:{self.process_manager['frontend_port']} (PID: {self.process_manager['vite_pid'] or 'N/A'})\n\n"
        status_text += f"💡 ArangoDB: {self.arango_connection['message']}\n"
        status_text += f"💡 SSH: {self.ssh_tunnel['message']}\n"
        status_text += f"💡 Процессы: {self.process_manager['message']}"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_stop_graph_viewer(self, arguments: dict) -> dict:
        """Остановить Graph Viewer"""
        stop_tunnel = arguments.get("stop_tunnel", False)
        force = arguments.get("force", False)
        
        status_text = f"🛑 Graph Viewer: Остановка компонентов\n"
        status_text += f"🔧 Параметры:\n"
        status_text += f"   🔌 Остановка туннеля: {stop_tunnel}\n"
        status_text += f"   ⚡ Принудительная остановка: {force}\n\n"
        
        # Остановка процессов
        if self.process_manager["manager"]:
            status_text += f"🔧 Остановка процессов...\n"
            status_text += f"   🚀 API сервер: остановлен\n"
            status_text += f"   ⚡ Vite сервер: остановлен\n"
        
        # Остановка SSH туннеля
        if stop_tunnel and self.ssh_tunnel["manager"]:
            status_text += f"🔌 Остановка SSH туннеля...\n"
            status_text += f"   SSH туннель: остановлен\n"
        
        status_text += f"\n✅ Компоненты остановлены успешно!"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_check_imports(self, arguments: dict) -> dict:
        """Диагностика импортов"""
        status_text = f"🔍 Проверка импортов и зависимостей\n\n"
        
        status_text += f"📦 Базовые модули:\n"
        for module, available in self.imports_status["basic"].items():
            status_text += f"   {'✅' if available else '❌'} {module}: {'Доступен' if available else 'Недоступен'}\n"
        
        status_text += f"\n🌐 Внешние модули:\n"
        for module, available in self.imports_status["external"].items():
            status_text += f"   {'✅' if available else '❌'} {module}: {'Доступен' if available else 'Недоступен'}\n"
        
        status_text += f"\n🎯 Graph Viewer модули:\n"
        for module, available in self.imports_status["graph_viewer"].items():
            status_text += f"   {'✅' if available else '❌'} {module}: {'Доступен' if available else 'Недоступен'}\n"
        
        all_available = (
            all(self.imports_status["basic"].values()) and
            all(self.imports_status["external"].values()) and
            all(self.imports_status["graph_viewer"].values())
        )
        
        if all_available:
            status_text += f"\n🎉 Все модули доступны - полная интеграция завершена!"
        else:
            status_text += f"\n⚠️  Некоторые модули недоступны"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_check_stubs(self, arguments: dict) -> dict:
        """Диагностика всех компонентов"""
        arango_status = self.arango_connection["status"]
        ssh_status = self.ssh_tunnel["status"]
        pm_status = self.process_manager["status"]
        
        status_text = f"🔍 Проверка всех компонентов (полная интеграция)\n\n"
        
        status_text += f"🗄️  ArangoDB подключение:\n"
        status_text += f"   Статус: {arango_status}\n"
        status_text += f"   Хост: {self.arango_connection['host']}\n"
        status_text += f"   База данных: {self.arango_connection['database']}\n"
        status_text += f"   💡 {self.arango_connection['message']}\n\n"
        
        status_text += f"🔌 SSH туннель:\n"
        status_text += f"   Статус: {ssh_status}\n"
        status_text += f"   Локальный порт: {self.ssh_tunnel['local_port']}\n"
        status_text += f"   Удаленный хост: {self.ssh_tunnel['remote_host']}\n"
        status_text += f"   PID: {self.ssh_tunnel['pid'] or 'N/A'}\n"
        status_text += f"   💡 {self.ssh_tunnel['message']}\n\n"
        
        status_text += f"🚀 API сервер:\n"
        status_text += f"   Статус: {pm_status}\n"
        status_text += f"   Порт: {self.process_manager['api_port']}\n"
        status_text += f"   PID: {self.process_manager['api_pid'] or 'N/A'}\n"
        status_text += f"   💡 {self.process_manager['message']}\n\n"
        
        status_text += f"⚡ Vite сервер:\n"
        status_text += f"   Статус: {pm_status}\n"
        status_text += f"   Порт: {self.process_manager['frontend_port']}\n"
        status_text += f"   PID: {self.process_manager['vite_pid'] or 'N/A'}\n"
        status_text += f"   💡 {self.process_manager['message']}\n\n"
        
        all_ok = (
            arango_status == "connected" and
            ssh_status == "connected" and
            pm_status in ["running", "partial", "stopped"]
        )
        
        if all_ok:
            status_text += f"🎉 Полная интеграция завершена - все компоненты готовы!"
        else:
            status_text += f"⚠️  Некоторые компоненты недоступны - проверьте конфигурацию"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_test_arango(self, arguments: dict) -> dict:
        """Тестирование ArangoDB"""
        arango_status = self.arango_connection["status"]
        arango_message = self.arango_connection["message"]
        
        status_text = f"🧪 Тестирование ArangoDB подключения\n\n"
        status_text += f"🔧 Конфигурация:\n"
        status_text += f"   Хост: {self.arango_connection['host']}\n"
        status_text += f"   База данных: {self.arango_connection['database']}\n"
        status_text += f"   Пользователь: {self.arango_connection['user']}\n\n"
        status_text += f"📊 Статус подключения:\n"
        status_text += f"   Статус: {arango_status}\n"
        status_text += f"   Сообщение: {arango_message}\n\n"
        
        if arango_status == "connected":
            try:
                db = self.arango_connection["connection"]
                properties = db.properties()
                
                status_text += f"✅ Тест подключения успешен!\n"
                status_text += f"📊 Информация о базе данных:\n"
                status_text += f"   Имя: {properties.get('name', 'N/A')}\n"
                status_text += f"   ID: {properties.get('id', 'N/A')}\n"
                status_text += f"   Путь: {properties.get('path', 'N/A')}\n"
                status_text += f"   Система: {properties.get('system', 'N/A')}\n\n"
                status_text += f"🎉 ArangoDB готов к работе с Graph Viewer!"
            except Exception as e:
                status_text += f"❌ Ошибка тестирования: {str(e)}"
        else:
            status_text += f"❌ ArangoDB недоступен"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_test_ssh(self, arguments: dict) -> dict:
        """Тестирование SSH туннеля"""
        ssh_status = self.ssh_tunnel["status"]
        ssh_message = self.ssh_tunnel["message"]
        
        status_text = f"🧪 Тестирование SSH туннеля\n\n"
        status_text += f"🔧 Конфигурация:\n"
        status_text += f"   Удаленный хост: {self.ssh_tunnel['remote_host']}\n"
        status_text += f"   Локальный порт: {self.ssh_tunnel['local_port']}\n"
        status_text += f"   Удаленный порт: {self.ssh_tunnel['remote_port']}\n\n"
        status_text += f"📊 Статус туннеля:\n"
        status_text += f"   Статус: {ssh_status}\n"
        status_text += f"   Сообщение: {ssh_message}\n"
        status_text += f"   PID: {self.ssh_tunnel['pid'] or 'N/A'}\n\n"
        
        if ssh_status == "connected":
            status_text += f"✅ SSH туннель активен!\n"
            status_text += f"🔗 Подключение: localhost:{self.ssh_tunnel['local_port']} → {self.ssh_tunnel['remote_host']}:{self.ssh_tunnel['remote_port']}\n"
            status_text += f"🎉 SSH туннель готов для Graph Viewer!"
        else:
            status_text += f"❌ SSH туннель недоступен"
        
        return {"content": [{"type": "text", "text": status_text}]}
    
    def _handle_get_selected_nodes(self, arguments: dict) -> dict:
        """Делегирование в обработчик получения выборки"""
        try:
            result = graph_viewer_manager.get_selected_nodes()
            
            # Всегда возвращаем message для отображения в чате
            return {
                "content": [{
                    "type": "text",
                    "text": result.get("message", "Нет данных")
                }]
            }
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Ошибка: {str(e)}"
                }]
            }
    
    def _handle_add_edge(self, arguments: dict) -> dict:
        """Обработка команды добавления ребра"""
        try:
            from_node = arguments.get("from_node")
            to_node = arguments.get("to_node")
            relation_type = arguments.get("relation_type", "related")
            projects = arguments.get("projects", [])
            
            if not from_node or not to_node:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ Ошибка: Не указаны обязательные параметры from_node и to_node"
                    }]
                }
            
            result = self.edge_manager.add_edge(
                from_node=from_node,
                to_node=to_node,
                relation_type=relation_type,
                projects=projects
            )
            
            if result['success']:
                from_label = from_node.split('/')[-1]
                to_label = to_node.split('/')[-1]
                text = f"✅ Связь создана!\n\n"
                text += f"📊 Детали:\n"
                text += f"   От: {from_label}\n"
                text += f"   К: {to_label}\n"
                text += f"   Тип: {relation_type}\n"
                text += f"   Проекты: {', '.join(projects) if projects else 'нет'}\n"
                text += f"   ID: {result['edge']['_id']}"
            else:
                text = f"❌ Ошибка создания связи\n\n"
                text += f"Причина: {result['error']}"
            
            return {"content": [{"type": "text", "text": text}]}
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Неожиданная ошибка: {str(e)}"
                }]
            }
    
    def _handle_update_edge(self, arguments: dict) -> dict:
        """Обработка команды обновления ребра"""
        try:
            edge_id = arguments.get("edge_id")
            
            if not edge_id:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ Ошибка: Не указан обязательный параметр edge_id"
                    }]
                }
            
            result = self.edge_manager.update_edge(
                edge_id=edge_id,
                from_node=arguments.get("from_node"),
                to_node=arguments.get("to_node"),
                relation_type=arguments.get("relation_type"),
                projects=arguments.get("projects")
            )
            
            if result['success']:
                text = f"✅ Связь обновлена!\n\n"
                text += f"📊 ID: {edge_id}\n"
                if arguments.get("from_node"):
                    text += f"   Новый from: {arguments['from_node'].split('/')[-1]}\n"
                if arguments.get("to_node"):
                    text += f"   Новый to: {arguments['to_node'].split('/')[-1]}\n"
                if arguments.get("relation_type"):
                    text += f"   Новый тип: {arguments['relation_type']}\n"
                if arguments.get("projects") is not None:
                    text += f"   Новые проекты: {', '.join(arguments['projects'])}\n"
            else:
                text = f"❌ Ошибка обновления связи\n\n"
                text += f"Причина: {result['error']}"
            
            return {"content": [{"type": "text", "text": text}]}
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Неожиданная ошибка: {str(e)}"
                }]
            }
    
    def _handle_delete_edge(self, arguments: dict) -> dict:
        """Обработка команды удаления ребра"""
        try:
            edge_id = arguments.get("edge_id")
            
            if not edge_id:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ Ошибка: Не указан обязательный параметр edge_id"
                    }]
                }
            
            result = self.edge_manager.delete_edge(edge_id)
            
            if result['success']:
                text = f"✅ Связь удалена!\n\n"
                text += f"📊 ID: {edge_id}"
            else:
                text = f"❌ Ошибка удаления связи\n\n"
                text += f"Причина: {result['error']}"
            
            return {"content": [{"type": "text", "text": text}]}
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Неожиданная ошибка: {str(e)}"
                }]
            }
    
    def _handle_check_edge_uniqueness(self, arguments: dict) -> dict:
        """Обработка команды проверки уникальности"""
        try:
            from_node = arguments.get("from_node")
            to_node = arguments.get("to_node")
            exclude_edge_id = arguments.get("exclude_edge_id")
            
            if not from_node or not to_node:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ Ошибка: Не указаны обязательные параметры from_node и to_node"
                    }]
                }
            
            result = self.edge_manager.check_edge_uniqueness(
                from_node=from_node,
                to_node=to_node,
                exclude_edge_id=exclude_edge_id
            )
            
            from_label = from_node.split('/')[-1]
            to_label = to_node.split('/')[-1]
            
            if result.get('is_unique'):
                text = f"✅ Связь уникальна!\n\n"
                text += f"📊 Проверка:\n"
                text += f"   От: {from_label}\n"
                text += f"   К: {to_label}\n"
                text += f"   Результат: Связи не существует\n\n"
                text += f"💡 Можно создать эту связь"
            else:
                text = f"⚠️ Связь НЕ уникальна!\n\n"
                text += f"📊 Проверка:\n"
                text += f"   От: {from_label}\n"
                text += f"   К: {to_label}\n"
                text += f"   Результат: {result.get('error', 'Связь уже существует')}\n\n"
                text += f"❌ Создание этой связи будет отклонено"
            
            return {"content": [{"type": "text", "text": text}]}
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Неожиданная ошибка: {str(e)}"
                }]
            }
    
    def run(self):
        """Основной цикл сервера"""
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params", {})
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {
                                "name": self.config["server"]["name"],
                                "version": self.config["server"]["version"]
                            }
                        }
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                    notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    print(json.dumps(notification))
                    sys.stdout.flush()
                
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": list(self.tools.values())}
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if tool_name in self.handlers:
                        result = self.handlers[tool_name](arguments)
                    else:
                        result = {
                            "content": [{
                                "type": "text",
                                "text": f"❌ Неизвестный инструмент: {tool_name}"
                            }]
                        }
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                
                elif method == "shutdown":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {}
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                    break
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr, flush=True)

def main():
    """Точка входа"""
    server = FedocMCPServer()
    server.run()

if __name__ == "__main__":
    main()
