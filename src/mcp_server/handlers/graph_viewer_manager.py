"""
MCP обработчик для управления системой визуализации графа
Интегрирует Graph Viewer в MCP-сервер для работы через Cursor AI

Версия 2.0 с поддержкой ConfigManager и профилей машин
"""

import sys
import webbrowser
from pathlib import Path
from typing import Optional, Dict
import importlib

# Добавляем путь к библиотекам
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Импортируем модули
import lib.graph_viewer.backend.config_manager
import lib.graph_viewer.backend.interactive_setup
import lib.graph_viewer.backend.tunnel_manager
import lib.graph_viewer.backend.process_manager

# Перезагружаем модули для получения последних изменений
importlib.reload(lib.graph_viewer.backend.config_manager)
importlib.reload(lib.graph_viewer.backend.interactive_setup)
importlib.reload(lib.graph_viewer.backend.tunnel_manager)
importlib.reload(lib.graph_viewer.backend.process_manager)

from lib.graph_viewer.backend import (
    ConfigManager, get_config,
    InteractiveSetup,
    TunnelManager, ProcessManager
)


# Перенаправление print в stderr для MCP протокола
def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    print(message, file=sys.stderr, flush=True)


# Глобальный экземпляр конфигурации (singleton)
_config = None

def get_or_create_config() -> ConfigManager:
    """Получить или создать ConfigManager"""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def open_graph_viewer(
    project: Optional[str] = None,
    auto_open_browser: bool = True
) -> Dict[str, any]:
    """
    Запустить систему визуализации графа в браузере
    
    Эта команда автоматически:
    1. Загружает конфигурацию (с профилем машины)
    2. Проверяет зависимости (первый запуск)
    3. Проверяет/создает SSH туннель к ArangoDB
    4. Запускает API сервер (если не запущен)
    5. Запускает Vite dev сервер (если не запущен)  
    6. Открывает браузер на интерфейсе визуализации
    
    Args:
        project: Фильтр по проекту (fepro, femsq, fedoc) или None для всех
        auto_open_browser: Автоматически открыть браузер
    
    Returns:
        Словарь со статусом запуска и URL интерфейса
    
    Примеры использования в Cursor AI:
        "Открой управление графом"
        "Запусти graph viewer для проекта FEPRO"
        "Покажи визуализацию"
    """
    try:
        # Загружаем конфигурацию
        log("\n📦 Загрузка конфигурации...")
        config = get_or_create_config()
        
        # Проверяем зависимости при первом запуске
        if config.is_first_run():
            log("\n🔧 Первый запуск - проверка зависимостей...")
            setup = InteractiveSetup(config)
            setup.check_all()
        
        # Инициализация менеджеров с конфигурацией
        tunnel_mgr = TunnelManager(config=config)
        process_mgr = ProcessManager(config=config)
        
        results = {
            "status": "success",
            "message": "Система визуализации графа запущена",
            "url": f"http://localhost:{config.get('ports.vite_server', 5173)}",
            "components": {}
        }
        
        # 1. Проверяем/создаем все SSH туннели
        log("\n🔌 Проверка SSH туннелей...")
        tunnel_ok = tunnel_mgr.ensure_all_tunnels()
        if not tunnel_ok:
            return {
                "status": "error",
                "message": "Не удалось создать SSH туннели",
                "details": f"Проверьте SSH доступ к серверу {config.get('remote_server.ssh_alias')}"
            }
        
        # Получаем статус всех туннелей
        tunnels_status = tunnel_mgr.get_status()
        results["components"]["ssh_tunnels"] = tunnels_status
        
        # Логируем статус каждого туннеля
        for name, tunnel in tunnels_status.items():
            if tunnel['status'] == 'connected':
                log(f"   ✓ {tunnel['name']} туннель активен (порт {tunnel['local_port']}, PID: {tunnel.get('pid', 'N/A')})")
            else:
                log(f"   ⚠️ {tunnel['name']} туннель не активен")
        
        # 2. Запускаем API сервер
        log("\n🚀 Проверка API сервера...")
        api_ok = process_mgr.start_api_server()
        if not api_ok:
            return {
                "status": "error",
                "message": "Не удалось запустить API сервер",
                "details": "Проверьте логи API сервера"
            }
        log(f"   ✓ API сервер запущен")
        
        # 3. Запускаем Vite dev сервер
        log("\n⚡ Проверка Vite сервера...")
        vite_ok = process_mgr.start_vite_server()
        if not vite_ok:
            return {
                "status": "error",
                "message": "Не удалось запустить Vite сервер",
                "details": "Проверьте логи Vite сервера"
            }
        log(f"   ✓ Vite сервер запущен")
        
        # Обновляем статус компонентов
        proc_status = process_mgr.get_status()
        results["components"]["api_server"] = f"running on port {proc_status['api_server']['port']}"
        results["components"]["vite_server"] = f"running on port {proc_status['vite_server']['port']}"
        
        # 4. Формируем URL с параметрами
        url = results["url"]
        if project:
            url += f"?project={project}"
            results["url"] = url
            results["message"] = f"Система визуализации графа запущена для проекта {project}"
        
        # 5. Открываем браузер с учетом WSL и разных ОС
        browser_setting = config.get('options.auto_open_browser', True)
        if auto_open_browser and browser_setting:
            log(f"\n🌐 Открываю браузер: {url}")
            
            # Проверяем специальную команду для браузера (например, WSL)
            browser_cmd = config.get('environment.browser_command')
            if browser_cmd:
                # WSL или специальная команда для открытия браузера
                import subprocess
                try:
                    subprocess.run(f'{browser_cmd} {url}', shell=True, check=False)
                except Exception as e:
                    log(f"⚠️ Ошибка открытия браузера через команду: {e}")
                    log(f"   Откройте вручную: {url}")
            else:
                # Обычная система - используем webbrowser
                webbrowser.open(url)
            
            results["browser_opened"] = True
        else:
            results["browser_opened"] = False
            log(f"\n🌐 Интерфейс доступен: {url}")
        
        log(f"\n✅ {results['message']}")
        log(f"📊 URL: {results['url']}")
        log(f"🖥️  Машина: {config.machine_name}")
        
        return results
        
    except Exception as e:
        log(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return {
            "status": "error",
            "message": f"Ошибка запуска Graph Viewer: {str(e)}",
            "details": str(e)
        }


def graph_viewer_status() -> Dict[str, any]:
    """
    Получить статус компонентов системы визуализации графа
    
    Returns:
        Словарь с детальным статусом всех компонентов
    
    Примеры использования в Cursor AI:
        "Проверь статус graph viewer"
        "Работает ли визуализация?"
        "Какие компоненты graph viewer запущены?"
    """
    try:
        # Загружаем конфигурацию
        config = get_or_create_config()
        
        tunnel_mgr = TunnelManager(config=config)
        process_mgr = ProcessManager(config=config)
        
        # Получаем статусы
        tunnels_status = tunnel_mgr.get_status()
        process_status = process_mgr.get_status()
        
        # Проверяем статус туннелей
        all_tunnels_ok = all(t.get('status') == 'connected' for t in tunnels_status.values()) if tunnels_status else True
        
        # Формируем результат
        result = {
            "overall_status": "running" if (
                all_tunnels_ok and
                process_status["overall_status"] == "running"
            ) else "stopped" if (
                not all_tunnels_ok and
                process_status["overall_status"] == "stopped"
            ) else "partial",
            "machine": config.machine_name,
            "components": {
                "ssh_tunnels": tunnels_status,
                "api_server": {
                    "status": process_status["api_server"]["status"],
                    "port": process_status["api_server"]["port"],
                    "pid": process_status["api_server"]["pid"]
                },
                "vite_server": {
                    "status": process_status["vite_server"]["status"],
                    "port": process_status["vite_server"]["port"],
                    "pid": process_status["vite_server"]["pid"]
                }
            },
            "url": f"http://localhost:{config.get('ports.vite_server', 5173)}",
            "ready": (
                all_tunnels_ok and
                process_status["overall_status"] == "running"
            )
        }
        
        # Выводим в удобном виде
        status_icon = "✅" if result["overall_status"] == "running" else "⚠️" if result["overall_status"] == "partial" else "❌"
        log(f"\n{status_icon} Общий статус: {result['overall_status']}")
        log(f"🖥️  Машина: {result['machine']}")
        log("\n🔧 Компоненты:")
        
        # Выводим туннели
        for name, tunnel in tunnels_status.items():
            tunnel_icon = "✅" if tunnel.get("status") == "connected" else "❌"
            pid_info = f" (PID: {tunnel.get('pid')})" if tunnel.get("pid") else ""
            log(f"   {tunnel_icon} {name}_tunnel: {tunnel.get('status', 'unknown')}{pid_info}")
        
        # Выводим процессы
        for name in ["api_server", "vite_server"]:
            comp = result["components"][name]
            comp_icon = "✅" if comp["status"] == "running" else "❌"
            pid_info = f" (PID: {comp['pid']})" if comp.get("pid") else ""
            log(f"   {comp_icon} {name}: {comp['status']}{pid_info}")
        
        if result["ready"]:
            log(f"\n🌐 Интерфейс доступен: {result['url']}")
        
        return result
        
    except Exception as e:
        log(f"\n❌ Ошибка проверки статуса: {e}")
        return {
            "status": "error",
            "message": f"Ошибка проверки статуса: {str(e)}"
        }


def stop_graph_viewer(
    stop_tunnel: bool = False,
    force: bool = False
) -> Dict[str, any]:
    """
    Остановить компоненты системы визуализации графа
    
    Args:
        stop_tunnel: Также закрыть SSH туннель (по умолчанию оставляем открытым)
        force: Принудительное завершение процессов (kill -9)
    
    Returns:
        Словарь со статусом остановки
    
    Примеры использования в Cursor AI:
        "Останови graph viewer"
        "Выключи визуализацию"
        "Закрой graph viewer и туннель"
    """
    try:
        config = get_or_create_config()
        
        tunnel_mgr = TunnelManager(config=config)
        process_mgr = ProcessManager(config=config)
        
        results = {
            "status": "success",
            "message": "Компоненты остановлены",
            "stopped": []
        }
        
        # Останавливаем процессы
        log("\n🛑 Останавливаю процессы...")
        
        if process_mgr.check_vite_server():
            process_mgr.stop_vite_server(force)
            results["stopped"].append("vite_server")
            log("   ✓ Vite сервер остановлен")
        
        if process_mgr.check_api_server():
            process_mgr.stop_api_server(force)
            results["stopped"].append("api_server")
            log("   ✓ API сервер остановлен")
        
        # Опционально останавливаем туннель
        if stop_tunnel and tunnel_mgr.check_tunnel():
            tunnel_mgr.close_tunnel()
            results["stopped"].append("ssh_tunnel")
            log("   ✓ SSH туннель закрыт")
        
        if not results["stopped"]:
            results["message"] = "Компоненты уже остановлены"
            log("   ℹ️  Компоненты уже были остановлены")
        else:
            results["message"] = f"Остановлено: {', '.join(results['stopped'])}"
        
        log(f"\n✅ {results['message']}")
        return results
        
    except Exception as e:
        log(f"\n❌ Ошибка остановки: {e}")
        return {
            "status": "error",
            "message": f"Ошибка остановки: {str(e)}"
        }


def get_selected_nodes() -> Dict[str, any]:
    """
    Получить объекты, выбранные пользователем в Graph Viewer
    
    Эта команда запрашивает у браузера текущую выборку узлов и рёбер
    через WebSocket соединение и возвращает детальную информацию.
    
    Returns:
        Словарь с выбранными узлами и рёбрами
    
    Примеры использования в Cursor AI:
        "Покажи выбранные объекты из Graph Viewer"
        "Что выбрано в графе?"
        "Покажи выбранные узлы"
    """
    try:
        # Загружаем конфигурацию
        config = get_or_create_config()
        api_port = config.get('ports.api_server', 8899)
        
        log("\n📋 Запрашиваю выборку из Graph Viewer...")
        
        # Делаем запрос к API серверу, который запросит данные у браузера через WebSocket
        import requests
        
        url = f'http://localhost:{api_port}/api/request_selection'
        response = requests.get(url, params={'timeout': '3.0'}, timeout=5)
        
        if response.status_code == 408:  # Timeout
            return {
                "status": "timeout",
                "message": "⏱️ Graph Viewer не ответил. Возможно:\n" +
                          "  • Graph Viewer не открыт в браузере\n" +
                          "  • WebSocket соединение не установлено\n" +
                          "  • Браузер не активен\n\n" +
                          "Попробуйте:\n" +
                          "  1. Открыть Graph Viewer: 'Открой graph viewer'\n" +
                          "  2. Выбрать объекты в графе (Ctrl+Click)\n" +
                          "  3. Повторить команду"
            }
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Ошибка получения выборки: HTTP {response.status_code}"
            }
        
        data = response.json()
        
        if data.get('status') != 'success':
            return {
                "status": "error",
                "message": data.get('message', 'Неизвестная ошибка')
            }
        
        selection = data.get('selection', {})
        nodes = selection.get('nodes', [])
        edges = selection.get('edges', [])
        
        if not nodes and not edges:
            return {
                "status": "empty",
                "message": "📭 Нет выбранных объектов\n\n" +
                          "Выберите узлы или рёбра в Graph Viewer:\n" +
                          "  • Кликните на узел для выбора\n" +
                          "  • Ctrl+Click для множественного выбора\n" +
                          "  • Клик на пустом месте для сброса выбора"
            }
        
        # Форматируем красивый вывод
        result_lines = ["✅ Выбрано в Graph Viewer:\n"]
        
        if nodes:
            result_lines.append(f"📦 Узлы ({len(nodes)}):")
            for i, node in enumerate(nodes, 1):
                node_id = node.get('id', node.get('_id', 'N/A'))
                node_name = node.get('label', node.get('name', node.get('key', 'Без названия')))
                node_key = node.get('key', node.get('_key', ''))
                
                # Определяем тип узла по префиксу ключа
                node_kind = node.get('kind', node.get('type', 'unknown'))
                if node_kind == 'unknown' and node_key:
                    if node_key.startswith('c:'):
                        node_kind = 'категория'
                    elif node_key.startswith('t:'):
                        node_kind = 'технология'
                    elif node_key.startswith('v:'):
                        node_kind = 'версия'
                result_lines.append(f"{i}. ID: {node_id}")
                if node_key:
                    result_lines.append(f"   Ключ: {node_key}")
                result_lines.append(f"   Название: {node_name}")
                result_lines.append(f"   Тип: {node_kind}")
                
                if node.get('description'):
                    desc = node['description'][:100]
                    if len(node['description']) > 100:
                        desc += '...'
                    result_lines.append(f"   Описание: {desc}")
                
                result_lines.append("")
        
        if edges:
            result_lines.append(f"🔗 Рёбра ({len(edges)}):")
            for i, edge in enumerate(edges, 1):
                edge_id = edge.get('id', edge.get('_id', 'N/A'))
                edge_from = edge.get('from', edge.get('_from', '?'))
                edge_to = edge.get('to', edge.get('_to', '?'))
                projects = edge.get('projects', [])
                
                result_lines.append(f"{i}. {edge_id}")
                result_lines.append(f"   От: {edge_from}")
                result_lines.append(f"   К: {edge_to}")
                
                if projects:
                    result_lines.append(f"   Проекты: {', '.join(projects)}")
                
                if edge.get('relationType'):
                    result_lines.append(f"   Тип связи: {edge['relationType']}")
                
                result_lines.append("")
        
        log(f"✓ Получено: {len(nodes)} узлов, {len(edges)} рёбер")
        
        return {
            "status": "success",
            "message": "\n".join(result_lines),
            "data": {
                "nodes": nodes,
                "edges": edges,
                "count": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "total": len(nodes) + len(edges)
                }
            }
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "❌ Не удалось подключиться к API серверу\n\n" +
                      "API сервер не запущен. Попробуйте:\n" +
                      "  1. Запустить Graph Viewer: 'Открой graph viewer'\n" +
                      "  2. Проверить статус: 'Проверь статус graph viewer'"
        }
    except Exception as e:
        log(f"\n❌ Ошибка получения выборки: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        return {
            "status": "error",
            "message": f"Ошибка получения выборки: {str(e)}"
        }


# Экспорт функций для регистрации в MCP сервере
__all__ = [
    'open_graph_viewer',
    'graph_viewer_status',
    'stop_graph_viewer',
    'get_selected_nodes'
]
