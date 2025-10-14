"""
Обработчик команд визуализации графов
Интегрирует библиотеку graph_viewer для работы через MCP
"""

import sys
from pathlib import Path

# Импорт библиотеки graph_viewer
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from lib.graph_viewer import ArangoGraphViewer

# TODO: Импортировать MCP декораторы когда будет полная реализация
# from mcp import tool

from ..config import (
    ARANGO_HOST, 
    ARANGO_DB, 
    ARANGO_USER, 
    ARANGO_PASSWORD, 
    COMMON_GRAPH_NAME
)


def show_graph(
    project: str = None,
    start_node: str = "canonical_nodes/c:backend",
    depth: int = 5,
    theme: str = "dark"
) -> str:
    """
    Визуализировать граф проекта в интерактивном браузере
    
    Args:
        project: Фильтр по проекту (fepro, femsq, fedoc) или None для всех
        start_node: Стартовая вершина для обхода
        depth: Глубина обхода (количество рёбер)
        theme: Тема оформления (dark/light)
    
    Returns:
        Сообщение о результате
    """
    try:
        viewer = ArangoGraphViewer(
            host=ARANGO_HOST,
            database=ARANGO_DB,
            username=ARANGO_USER,
            password=ARANGO_PASSWORD
        )
        
        edges = viewer.fetch_graph(
            graph_name=COMMON_GRAPH_NAME,
            project_filter=project,
            start_node=start_node,
            depth=depth
        )
        
        if not edges:
            return f"⚠️ Граф пуст или не найден для проекта '{project or 'все'}'"
        
        output_file = viewer.visualize(
            edges=edges,
            project_filter=project,
            theme=theme
        )
        
        project_name = project or "все проекты"
        nodes_count = len(set(e['from_key'] for e in edges) | set(e['to_key'] for e in edges))
        
        return (
            f"✅ Граф проекта '{project_name}' открыт в браузере\n"
            f"📁 Файл: {output_file}\n"
            f"📊 Узлов: {nodes_count}\n"
            f"🔗 Рёбер: {len(edges)}"
        )
        
    except Exception as e:
        return f"❌ Ошибка визуализации: {str(e)}"


def query_graph(aql_query: str) -> dict:
    """
    Выполнить AQL запрос к графу проектов
    
    Args:
        aql_query: AQL запрос
    
    Returns:
        Результат запроса
    """
    # TODO: Реализовать выполнение AQL запросов
    return {"status": "not_implemented", "message": "Функция в разработке"}
