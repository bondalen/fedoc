#!/usr/bin/env python3
"""
Управление процессами API сервера и Vite dev сервера
"""

import subprocess
import time
import re
import os
import signal
import sys
from typing import Optional, Dict
from pathlib import Path

# Перенаправление print в stderr для MCP протокола
def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    log(message, file=sys.stderr, flush=True)


class ProcessManager:
    """Менеджер процессов для Graph Viewer компонентов"""
    
    def __init__(
        self,
        graph_viewer_root: Optional[Path] = None,
        arango_password: str = "fedoc_dev_2025"
    ):
        """
        Args:
            graph_viewer_root: Корневая директория graph_viewer
            arango_password: Пароль для ArangoDB
        """
        if graph_viewer_root is None:
            # Определяем путь относительно этого файла
            graph_viewer_root = Path(__file__).parent.parent
        
        self.graph_viewer_root = Path(graph_viewer_root)
        self.backend_dir = self.graph_viewer_root / "backend"
        self.frontend_dir = self.graph_viewer_root / "frontend"
        self.project_root = self.graph_viewer_root.parent.parent.parent
        self.venv_python = self.project_root / "venv" / "bin" / "python"
        self.arango_password = arango_password
        
    def _find_process(self, pattern: str) -> Optional[int]:
        """
        Найти PID процесса по паттерну
        
        Args:
            pattern: Регулярное выражение для поиска процесса
            
        Returns:
            PID процесса или None
        """
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if re.search(pattern, line) and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            return int(parts[1])
                        except ValueError:
                            continue
            
            return None
            
        except subprocess.CalledProcessError:
            return None
    
    def check_api_server(self) -> Optional[int]:
        """
        Проверить работает ли API сервер
        
        Returns:
            PID процесса или None
        """
        return self._find_process(r"python.*api_server\.py")
    
    def check_vite_server(self) -> Optional[int]:
        """
        Проверить работает ли Vite dev сервер
        
        Returns:
            PID процесса или None
        """
        return self._find_process(r"node.*vite")
    
    def start_api_server(self) -> bool:
        """
        Запустить API сервер если еще не запущен
        
        Returns:
            True если сервер запущен, False при ошибке
        """
        # Проверяем существующий процесс
        pid = self.check_api_server()
        if pid:
            log(f"✓ API сервер уже запущен (PID: {pid})")
            return True
        
        try:
            # Запускаем API сервер в фоне
            api_script = self.backend_dir / "api_server.py"
            log_file = Path("/tmp/graph_viewer_api.log")
            
            with open(log_file, "w") as log:
                subprocess.Popen(
                    [
                        str(self.venv_python),
                        str(api_script),
                        "--db-password", self.arango_password
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=self.backend_dir,
                    start_new_session=True
                )
            
            # Даем время на запуск
            time.sleep(2)
            
            # Проверяем что процесс запустился
            pid = self.check_api_server()
            if pid:
                log(f"✓ API сервер запущен (PID: {pid})")
                return True
            else:
                log(f"⚠ API сервер не запустился. Проверьте лог: {log_file}")
                # Показываем последние строки лога
                try:
                    with open(log_file, "r") as log:
                        lines = log.readlines()
                        if lines:
                            log("Последние строки лога:")
                            for line in lines[-5:]:
                                log(f"  {line.rstrip()}")
                except:
                    pass
                return False
                
        except Exception as e:
            log(f"✗ Ошибка запуска API сервера: {e}")
            return False
    
    def start_vite_server(self) -> bool:
        """
        Запустить Vite dev сервер если еще не запущен
        
        Returns:
            True если сервер запущен, False при ошибке
        """
        # Проверяем существующий процесс
        pid = self.check_vite_server()
        if pid:
            log(f"✓ Vite сервер уже запущен (PID: {pid})")
            return True
        
        try:
            # Запускаем Vite в фоне
            log_file = Path("/tmp/graph_viewer_vite.log")
            
            with open(log_file, "w") as log:
                subprocess.Popen(
                    ["npm", "run", "dev"],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=self.frontend_dir,
                    start_new_session=True
                )
            
            # Даем время на запуск (Vite запускается быстро)
            time.sleep(3)
            
            # Проверяем что процесс запустился
            pid = self.check_vite_server()
            if pid:
                log(f"✓ Vite сервер запущен (PID: {pid})")
                return True
            else:
                log(f"⚠ Vite сервер не запустился. Проверьте лог: {log_file}")
                return False
                
        except Exception as e:
            log(f"✗ Ошибка запуска Vite сервера: {e}")
            return False
    
    def stop_api_server(self, force: bool = False) -> bool:
        """
        Остановить API сервер
        
        Args:
            force: Использовать SIGKILL вместо SIGTERM
            
        Returns:
            True если сервер остановлен, False при ошибке
        """
        pid = self.check_api_server()
        if not pid:
            log("⚠ API сервер не запущен")
            return True
        
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            time.sleep(1)
            
            # Проверяем что процесс остановлен
            if self.check_api_server() is None:
                log(f"✓ API сервер остановлен (PID: {pid})")
                return True
            else:
                log(f"⚠ API сервер не остановился, пробуем force kill...")
                os.kill(pid, signal.SIGKILL)
                return True
                
        except Exception as e:
            log(f"✗ Ошибка остановки API сервера: {e}")
            return False
    
    def stop_vite_server(self, force: bool = False) -> bool:
        """
        Остановить Vite dev сервер
        
        Args:
            force: Использовать SIGKILL вместо SIGTERM
            
        Returns:
            True если сервер остановлен, False при ошибке
        """
        pid = self.check_vite_server()
        if not pid:
            log("⚠ Vite сервер не запущен")
            return True
        
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            time.sleep(1)
            
            # Проверяем что процесс остановлен
            if self.check_vite_server() is None:
                log(f"✓ Vite сервер остановлен (PID: {pid})")
                return True
            else:
                log(f"⚠ Vite сервер не остановился, пробуем force kill...")
                os.kill(pid, signal.SIGKILL)
                return True
                
        except Exception as e:
            log(f"✗ Ошибка остановки Vite сервера: {e}")
            return False
    
    def get_status(self) -> Dict[str, any]:
        """
        Получить статус всех процессов
        
        Returns:
            Словарь со статусом процессов
        """
        api_pid = self.check_api_server()
        vite_pid = self.check_vite_server()
        
        return {
            "api_server": {
                "status": "running" if api_pid else "stopped",
                "pid": api_pid,
                "port": 8899
            },
            "vite_server": {
                "status": "running" if vite_pid else "stopped",
                "pid": vite_pid,
                "port": 5173
            },
            "overall_status": "running" if (api_pid and vite_pid) else (
                "partial" if (api_pid or vite_pid) else "stopped"
            )
        }
    
    def start_all(self) -> bool:
        """
        Запустить все компоненты
        
        Returns:
            True если все компоненты запущены, False при ошибке
        """
        api_ok = self.start_api_server()
        vite_ok = self.start_vite_server()
        
        return api_ok and vite_ok
    
    def stop_all(self, force: bool = False) -> bool:
        """
        Остановить все компоненты
        
        Args:
            force: Использовать force kill
            
        Returns:
            True если все компоненты остановлены
        """
        api_ok = self.stop_api_server(force)
        vite_ok = self.stop_vite_server(force)
        
        return api_ok and vite_ok


if __name__ == "__main__":
    # Тестирование
    manager = ProcessManager()
    
    log("Проверка процессов...")
    status = manager.get_status()
    log(f"Статус: {status}")
    
    if status["overall_status"] != "running":
        log("\nЗапуск процессов...")
        success = manager.start_all()
        if success:
            log("\nПроцессы запущены!")
            status = manager.get_status()
            log(f"Новый статус: {status}")








