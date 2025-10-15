#!/usr/bin/env python3
"""
Управление SSH туннелями к удаленному ArangoDB серверу
"""

import subprocess
import re
import sys
from typing import Optional, Dict

# Перенаправление print в stderr для MCP протокола
def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    log(message, file=sys.stderr, flush=True)


class TunnelManager:
    """Менеджер SSH туннелей для доступа к удаленному ArangoDB"""
    
    def __init__(
        self,
        remote_host: str = "vuege-server",
        local_port: int = 8529,
        remote_port: int = 8529
    ):
        """
        Args:
            remote_host: Имя хоста из ~/.ssh/config или IP адрес
            local_port: Локальный порт для туннеля
            remote_port: Удаленный порт ArangoDB
        """
        self.remote_host = remote_host
        self.local_port = local_port
        self.remote_port = remote_port
        
    def check_tunnel(self) -> Optional[int]:
        """
        Проверить существующий SSH туннель
        
        Returns:
            PID процесса если туннель активен, None если нет
        """
        try:
            # Поиск процесса SSH с туннелем на нужный порт
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Ищем строку вида: ssh -f -N -L 8529:localhost:8529 vuege-server
            pattern = rf"ssh.*-L\s+{self.local_port}:localhost:{self.remote_port}.*{self.remote_host}"
            
            for line in result.stdout.split('\n'):
                if re.search(pattern, line):
                    # Извлекаем PID (второй столбец)
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            return int(parts[1])
                        except ValueError:
                            continue
            
            return None
            
        except subprocess.CalledProcessError:
            return None
    
    def create_tunnel(self) -> bool:
        """
        Создать SSH туннель если его нет
        
        Returns:
            True если туннель создан или уже существует, False при ошибке
        """
        # Проверяем существующий туннель
        existing_pid = self.check_tunnel()
        if existing_pid:
            log(f"✓ SSH туннель уже активен (PID: {existing_pid})")
            return True
        
        try:
            # Создаем новый туннель
            # -f: фоновый режим
            # -N: не выполнять команды
            # -L: локальный форвардинг портов
            subprocess.run(
                [
                    "ssh",
                    "-f", "-N",
                    "-L", f"{self.local_port}:localhost:{self.remote_port}",
                    self.remote_host
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Проверяем что туннель создан
            pid = self.check_tunnel()
            if pid:
                log(f"✓ SSH туннель создан (PID: {pid})")
                return True
            else:
                log("⚠ Туннель не найден после создания")
                return False
                
        except subprocess.CalledProcessError as e:
            log(f"✗ Ошибка создания SSH туннеля: {e.stderr}")
            return False
    
    def close_tunnel(self) -> bool:
        """
        Закрыть SSH туннель
        
        Returns:
            True если туннель закрыт, False при ошибке
        """
        pid = self.check_tunnel()
        if not pid:
            log("⚠ SSH туннель не найден")
            return True
        
        try:
            subprocess.run(["kill", str(pid)], check=True)
            log(f"✓ SSH туннель остановлен (PID: {pid})")
            return True
        except subprocess.CalledProcessError as e:
            log(f"✗ Ошибка остановки туннеля: {e}")
            return False
    
    def get_status(self) -> Dict[str, any]:
        """
        Получить статус SSH туннеля
        
        Returns:
            Словарь со статусом туннеля
        """
        pid = self.check_tunnel()
        
        return {
            "status": "connected" if pid else "disconnected",
            "pid": pid,
            "local_port": self.local_port,
            "remote_port": self.remote_port,
            "remote_host": self.remote_host
        }
    
    def ensure_tunnel(self) -> bool:
        """
        Убедиться что туннель активен (создать если нужно)
        
        Returns:
            True если туннель активен, False при ошибке
        """
        pid = self.check_tunnel()
        if pid:
            return True
        return self.create_tunnel()


if __name__ == "__main__":
    # Тестирование
    manager = TunnelManager()
    
    log("Проверка туннеля...")
    status = manager.get_status()
    log(f"Статус: {status}")
    
    if status["status"] == "disconnected":
        log("\nСоздание туннеля...")
        success = manager.create_tunnel()
        if success:
            log("Туннель успешно создан!")
            status = manager.get_status()
            log(f"Новый статус: {status}")








