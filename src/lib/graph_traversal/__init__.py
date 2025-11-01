"""
Библиотека для обхода графа проектов (sys-001)

Модули:
- subgraph_builder: Построение подграфа проекта
- numbering: Система нумерации 01-zz
- traverser: Обход графа вниз (DFS)
- markdown_generator: Генерация Markdown вывода
"""

from .subgraph_builder import SubgraphBuilder
from .numbering import Numbering01zz
from .traverser import GraphTraverser
from .markdown_generator import MarkdownGenerator

__all__ = [
    'SubgraphBuilder',
    'Numbering01zz',
    'GraphTraverser',
    'MarkdownGenerator',
]

__version__ = '1.0.0'

