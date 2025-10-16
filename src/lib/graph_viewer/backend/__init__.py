"""
Backend модули для Graph Viewer
Управление процессами, туннелями, конфигурацией и API для системы визуализации графа
"""

from .config_manager import ConfigManager, get_config
from .interactive_setup import InteractiveSetup
from .tunnel_manager import TunnelManager
from .process_manager import ProcessManager

__all__ = [
    'ConfigManager', 'get_config',
    'InteractiveSetup',
    'TunnelManager', 'ProcessManager'
]











