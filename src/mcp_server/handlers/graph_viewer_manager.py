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
        
        # 1. Проверяем/создаем SSH туннель
        log("\n🔌 Проверка SSH туннеля...")
        tunnel_ok = tunnel_mgr.ensure_tunnel()
        if not tunnel_ok:
            return {
                "status": "error",
                "message": "Не удалось создать SSH туннель к ArangoDB",
                "details": f"Проверьте SSH доступ к серверу {config.get('remote_server.ssh_alias')}"
            }
        
        tunnel_status = tunnel_mgr.get_status()
        results["components"]["ssh_tunnel"] = f"active on port {tunnel_status['local_port']}"
        log(f"   ✓ SSH туннель активен (PID: {tunnel_status.get('pid', 'N/A')})")
        
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
        
        # 5. Открываем браузер
        browser_setting = config.get('options.auto_open_browser', True)
        if auto_open_browser and browser_setting:
            log(f"\n🌐 Открываю браузер: {url}")
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
        tunnel_status = tunnel_mgr.get_status()
        process_status = process_mgr.get_status()
        
        # Формируем результат
        result = {
            "overall_status": "running" if (
                tunnel_status["status"] == "connected" and
                process_status["overall_status"] == "running"
            ) else "stopped" if (
                tunnel_status["status"] == "disconnected" and
                process_status["overall_status"] == "stopped"
            ) else "partial",
            "machine": config.machine_name,
            "components": {
                "ssh_tunnel": {
                    "status": tunnel_status["status"],
                    "port": tunnel_status["local_port"],
                    "remote": tunnel_status["remote_host"],
                    "pid": tunnel_status.get("pid")
                },
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
                tunnel_status["status"] == "connected" and
                process_status["overall_status"] == "running"
            )
        }
        
        # Выводим в удобном виде
        status_icon = "✅" if result["overall_status"] == "running" else "⚠️" if result["overall_status"] == "partial" else "❌"
        log(f"\n{status_icon} Общий статус: {result['overall_status']}")
        log(f"🖥️  Машина: {result['machine']}")
        log("\n🔧 Компоненты:")
        for name, comp in result["components"].items():
            comp_icon = "✅" if comp["status"] in ["connected", "running"] else "❌"
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


# Экспорт функций для регистрации в MCP сервере
__all__ = [
    'open_graph_viewer',
    'graph_viewer_status',
    'stop_graph_viewer'
]
