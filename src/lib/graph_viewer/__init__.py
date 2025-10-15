"""
Библиотека визуализации графов ArangoDB для проекта fedoc
Современная архитектура с Vue.js фронтендом и REST API
"""

from .backend import TunnelManager, ProcessManager

__version__ = "0.2.0"
__all__ = ["TunnelManager", "ProcessManager"]
