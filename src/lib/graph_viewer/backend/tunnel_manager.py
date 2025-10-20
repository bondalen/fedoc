#!/usr/bin/env python3
"""
Управление SSH туннелями к удаленному серверу
Поддержка нескольких туннелей (PostgreSQL, ArangoDB, etc.)
"""

import subprocess
import re
import sys
from typing import Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .config_manager import ConfigManager

# Перенаправление print в stderr для MCP протокола
def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    print(message, file=sys.stderr, flush=True)


class TunnelManager:
    """Менеджер SSH туннелей (поддержка нескольких туннелей)"""
    
    def __init__(
        self,
        config: Optional['ConfigManager'] = None,
        remote_host: Optional[str] = None,
        local_port: Optional[int] = None,
        remote_port: Optional[int] = None
    ):
        """
        Args:
            config: Менеджер конфигурации (рекомендуется)
            remote_host: Имя хоста из ~/.ssh/config или IP адрес (если без config)
            local_port: Локальный порт для туннеля (если без config, legacy mode)
            remote_port: Удаленный порт сервера (если без config, legacy mode)
        """
        self.config = config
        self.tunnels = {}  # Словарь активных туннелей
        
        if config is not None:
            # Новый способ - через конфигурацию с поддержкой нескольких туннелей
            self.remote_host = config.get('remote_server.ssh_alias', 'fedoc-server')
            
            # PostgreSQL туннель (основной)
            if config.get('postgres.enabled', True):
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
            
            # Legacy mode: если нет туннелей в конфиге, создать дефолтный
            if not self.tunnels:
                self.tunnels['default'] = {
                    'local_port': config.get('ports.ssh_tunnel', 8529),
                    'remote_port': config.get('ports.ssh_tunnel', 8529),
                    'name': 'Default',
                    'pid': None
                }
        else:
            # Старый способ - напрямую через параметры (обратная совместимость)
            self.remote_host = remote_host or "fedoc-server"
            self.tunnels['default'] = {
                'local_port': local_port or 8529,
                'remote_port': remote_port or 8529,
                'name': 'Default',
                'pid': None
            }
        
        # Для обратной совместимости - свойства первого туннеля
        first_tunnel = list(self.tunnels.values())[0] if self.tunnels else None
        if first_tunnel:
            self.local_port = first_tunnel['local_port']
            self.remote_port = first_tunnel['remote_port']
        else:
            self.local_port = 8529
            self.remote_port = 8529
    
    def _check_single_tunnel(self, local_port: int, remote_port: int) -> Optional[int]:
        """
        Проверить существующий SSH туннель по портам
        
        Args:
            local_port: Локальный порт
            remote_port: Удаленный порт
            
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
            
            # Ищем строку вида: ssh -f -N -L 15432:localhost:5432 fedoc-server
            pattern = rf"ssh.*-L\s+{local_port}:localhost:{remote_port}.*{self.remote_host}"
            
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
    
    def check_tunnel(self, tunnel_name: Optional[str] = None) -> Optional[int]:
        """
        Проверить существующий SSH туннель
        
        Args:
            tunnel_name: Имя туннеля ('postgres', 'arango', etc.) или None для первого
            
        Returns:
            PID процесса если туннель активен, None если нет
        """
        if tunnel_name is None:
            # Обратная совместимость - проверить первый туннель
            tunnel_name = list(self.tunnels.keys())[0] if self.tunnels else None
        
        if tunnel_name not in self.tunnels:
            return None
        
        tunnel = self.tunnels[tunnel_name]
        return self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
    
    def create_tunnel(self, tunnel_name: Optional[str] = None) -> bool:
        """
        Создать SSH туннель если его нет
        
        Args:
            tunnel_name: Имя туннеля ('postgres', 'arango', etc.) или None для первого
            
        Returns:
            True если туннель создан или уже существует, False при ошибке
        """
        if tunnel_name is None:
            # Обратная совместимость - создать первый туннель
            tunnel_name = list(self.tunnels.keys())[0] if self.tunnels else None
        
        if tunnel_name not in self.tunnels:
            log(f"⚠️ Туннель '{tunnel_name}' не найден в конфигурации")
            return False
        
        tunnel = self.tunnels[tunnel_name]
        
        # Проверяем существующий туннель
        existing_pid = self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
        if existing_pid:
            log(f"✓ {tunnel['name']} туннель уже активен (PID: {existing_pid})")
            tunnel['pid'] = existing_pid
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
                    "-L", f"{tunnel['local_port']}:localhost:{tunnel['remote_port']}",
                    self.remote_host
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Проверяем что туннель создан
            pid = self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
            if pid:
                log(f"✓ {tunnel['name']} туннель создан (PID: {pid}, {tunnel['local_port']}→{tunnel['remote_port']})")
                tunnel['pid'] = pid
                return True
            else:
                log(f"⚠️ {tunnel['name']} туннель не найден после создания")
                return False
                
        except subprocess.CalledProcessError as e:
            log(f"✗ Ошибка создания {tunnel['name']} туннеля: {e.stderr}")
            return False
    
    def ensure_all_tunnels(self) -> bool:
        """
        Убедиться что все настроенные туннели активны (создать если нужно)
        
        Returns:
            True если все туннели активны, False если хотя бы один не удалось создать
        """
        success = True
        for tunnel_name in self.tunnels.keys():
            if not self.create_tunnel(tunnel_name):
                success = False
        return success
    
    def close_tunnel(self, tunnel_name: Optional[str] = None) -> bool:
        """
        Закрыть SSH туннель
        
        Args:
            tunnel_name: Имя туннеля или None для первого
            
        Returns:
            True если туннель закрыт, False при ошибке
        """
        if tunnel_name is None:
            # Обратная совместимость - закрыть первый туннель
            tunnel_name = list(self.tunnels.keys())[0] if self.tunnels else None
        
        if tunnel_name not in self.tunnels:
            return False
        
        tunnel = self.tunnels[tunnel_name]
        pid = self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
        
        if not pid:
            log(f"⚠️ {tunnel['name']} туннель не найден")
            return True
        
        try:
            subprocess.run(["kill", str(pid)], check=True)
            log(f"✓ {tunnel['name']} туннель остановлен (PID: {pid})")
            tunnel['pid'] = None
            return True
        except subprocess.CalledProcessError as e:
            log(f"✗ Ошибка остановки {tunnel['name']} туннеля: {e}")
            return False
    
    def close_all_tunnels(self) -> bool:
        """
        Закрыть все туннели
        
        Returns:
            True если все туннели закрыты, False при ошибках
        """
        success = True
        for tunnel_name in self.tunnels.keys():
            if not self.close_tunnel(tunnel_name):
                success = False
        return success
    
    def get_status(self, tunnel_name: Optional[str] = None) -> Dict[str, any]:
        """
        Получить статус SSH туннеля(ей)
        
        Args:
            tunnel_name: Имя конкретного туннеля или None для всех
            
        Returns:
            Словарь со статусом туннеля (если tunnel_name указан)
            или словарь всех туннелей (если None)
        """
        if tunnel_name is not None:
            # Статус конкретного туннеля (обратная совместимость)
            if tunnel_name not in self.tunnels:
                return {"status": "not_configured"}
            
            tunnel = self.tunnels[tunnel_name]
            pid = self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
            
            return {
                "status": "connected" if pid else "disconnected",
                "pid": pid,
                "local_port": tunnel['local_port'],
                "remote_port": tunnel['remote_port'],
                "remote_host": self.remote_host,
                "name": tunnel['name']
            }
        else:
            # Статус всех туннелей (новый формат)
            status = {}
            for name, tunnel in self.tunnels.items():
                pid = self._check_single_tunnel(tunnel['local_port'], tunnel['remote_port'])
                tunnel['pid'] = pid
                status[name] = {
                    'name': tunnel['name'],
                    'local_port': tunnel['local_port'],
                    'remote_port': tunnel['remote_port'],
                    'status': 'connected' if pid else 'disconnected',
                    'pid': pid
                }
            return status
    
    def ensure_tunnel(self) -> bool:
        """
        Убедиться что туннель активен (создать если нужно)
        Обратная совместимость - работает с первым туннелем
        
        Returns:
            True если туннель активен, False при ошибке
        """
        tunnel_name = list(self.tunnels.keys())[0] if self.tunnels else None
        if tunnel_name is None:
            return False
        return self.create_tunnel(tunnel_name)


if __name__ == "__main__":
    # Тестирование
    manager = TunnelManager()
    
    log("Проверка туннелей...")
    status = manager.get_status()
    log(f"Статус: {status}")
    
    log("\nСоздание всех туннелей...")
    success = manager.ensure_all_tunnels()
    if success:
        log("Все туннели успешно созданы!")
        status = manager.get_status()
        log(f"Новый статус: {status}")
