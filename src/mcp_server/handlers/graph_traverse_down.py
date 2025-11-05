"""
MCP-команда graph_traverse_down

Обход графа проекта вниз от узла (реализация sys-001)
"""

import sys
from pathlib import Path

# Добавить путь к библиотеке
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.graph_traversal import SubgraphBuilder, GraphTraverser, MarkdownGenerator


def graph_traverse_down(
    project: str,
    start_node: str = None,
    format: str = "markdown",
    audience: str = "ai",
    db_config: dict = None
) -> str:
    """
    Обход графа проекта вниз от стартового узла (sys-001)
    
    Args:
        project: Ключ проекта (fedoc, fepro, femsq)
        start_node: Стартовый узел (по умолчанию c:project)
        format: Формат вывода (markdown | json) [MVP: только markdown]
        audience: Целевая аудитория (human | ai) [MVP: только ai]
        
    Returns:
        Markdown документ с обходом графа
        
    Raises:
        ValueError: Неверные параметры или проект не найден
        Exception: Ошибки подключения к БД
        
    Examples:
        >>> graph_traverse_down("fedoc")
        # Обход графа: проект fedoc от узла c:project
        ...
        
        >>> graph_traverse_down("fedoc", start_node="c:backend")
        # Обход графа: проект fedoc от узла c:backend
        ...
    """
    # Валидация параметров
    valid_projects = ['fedoc', 'fepro', 'femsq']
    if project not in valid_projects:
        raise ValueError(f"Неверный проект '{project}'. Допустимые: {', '.join(valid_projects)}")
    
    # MVP: поддержка только markdown + ai
    if format != "markdown":
        raise ValueError(f"MVP: поддерживается только format='markdown', получено '{format}'")
    
    if audience != "ai":
        raise ValueError(f"MVP: поддерживается только audience='ai', получено '{audience}'")
    
    try:
        # Конфигурация БД (используем переданную или значения по умолчанию)
        if db_config is None:
            import os
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', '15432')),
                'database': os.getenv('POSTGRES_DB', 'fedoc'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'fedoc_test_2025')
            }
        
        # Шаг 1: Построить подграф проекта
        builder = SubgraphBuilder(db_config)
        subgraph = builder.build(project)
        
        # Шаг 2: Найти стартовый узел
        traverser = GraphTraverser(subgraph)
        start_node_id = traverser.find_start_node(start_node)
        
        # Получить ключ стартового узла для метаданных
        start_node_data = subgraph.get_node(start_node_id)
        start_node_key = start_node_data.get('arango_key', start_node or 'c:project')
        
        # Шаг 3: Обойти граф
        tree = traverser.traverse(start_node_id)
        
        # Шаг 4: Получить статистику
        stats = traverser.get_stats()
        
        # Шаг 5: Сгенерировать Markdown
        generator = MarkdownGenerator(project)
        markdown = generator.generate(tree, stats, start_node_key)
        
        return markdown
        
    except ValueError as e:
        # Ошибки валидации или поиска узлов
        raise ValueError(f"Ошибка обхода графа: {e}")
    
    except Exception as e:
        # Ошибки БД или другие
        raise Exception(f"Ошибка выполнения команды: {e}")


# Для тестирования
if __name__ == "__main__":
    try:
        result = graph_traverse_down("fedoc")
        print(result)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

