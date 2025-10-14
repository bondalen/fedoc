#!/usr/bin/env python3
"""
fedoc MCP Server
Сервер для интеграции с Cursor AI для управления проектной документацией
"""

import sys
import json
from pathlib import Path

# Добавить src в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Базовая реализация MCP-сервера (будет расширена)
class FedocMCPServer:
    """Базовый класс MCP-сервера fedoc"""
    
    def __init__(self):
        self.name = "fedoc"
        self.version = "0.1.0"
        self.tools = []
        
    def register_tool(self, tool_func):
        """Зарегистрировать инструмент"""
        self.tools.append(tool_func)
        
    def run(self):
        """Запустить сервер"""
        print(f"🚀 {self.name} MCP Server v{self.version} запущен")
        print(f"📊 Зарегистрировано инструментов: {len(self.tools)}")
        
        # TODO: Реализовать полный MCP протокол
        # Пока это заглушка для базовой структуры
        print("⚠️  Полная реализация MCP протокола в разработке")
        print("💡 Используйте graph_viewer напрямую: dev/tools/view-graph.sh")


def main():
    """Главная функция запуска MCP-сервера"""
    server = FedocMCPServer()
    
    # TODO: Импортировать и регистрировать обработчики
    # from handlers import graph_visualizer, documentation, projects, rules
    # server.register_tool(graph_visualizer.show_graph)
    # server.register_tool(documentation.get_project_docs)
    # server.register_tool(projects.list_projects)
    # server.register_tool(rules.get_rules)
    
    print("📋 Планируемые команды:")
    print("  - show_graph: Визуализировать граф проекта")
    print("  - query_graph: Выполнить AQL запрос к графу")
    print("  - get_project_docs: Получить документацию проекта")
    print("  - list_projects: Список всех проектов")
    print("  - get_rules: Получить правила для артефакта")
    
    server.run()


if __name__ == "__main__":
    main()
