"""
Обход графа вниз (DFS) с нумерацией 01-zz

Реализует принцип sys-001: обход от узла вниз по исходящим рёбрам.
"""

from typing import Dict, Optional, Set
from .subgraph_builder import Subgraph
from .numbering import Numbering01zz


class GraphTraverser:
    """Обход графа вниз с нумерацией"""
    
    def __init__(self, subgraph: Subgraph):
        """
        Args:
            subgraph: Подграф проекта для обхода
        """
        self.subgraph = subgraph
        self.numbering = Numbering01zz()
        self.visited: Dict[int, str] = {}  # {node_id: path}
        self.multi_parent_refs: Dict[str, list] = {}  # {arango_key: [paths]}
    
    def traverse(self, start_node_id: int) -> Dict:
        """
        Обойти граф вниз от стартового узла
        
        Args:
            start_node_id: ID стартового узла
            
        Returns:
            Дерево обхода с нумерацией
        """
        self.visited = {}
        self.multi_parent_refs = {}
        
        return self._traverse_recursive(start_node_id, path="01")
    
    def _traverse_recursive(
        self, 
        node_id: int, 
        path: str, 
        edge_type: Optional[str] = None
    ) -> Dict:
        """
        Рекурсивный обход с обработкой повторных включений
        
        Args:
            node_id: ID узла
            path: Путь узла (например, "01.01.02")
            edge_type: Тип связи с родителем
            
        Returns:
            Словарь с данными узла и дочерними узлами
        """
        node = self.subgraph.get_node(node_id)
        if not node:
            return {}
        
        arango_key = node.get('arango_key')
        
        # Проверка на повторное посещение
        if node_id in self.visited:
            # Повторное включение — только ссылка
            first_path = self.visited[node_id]
            
            # Записать в статистику множественных родителей
            if arango_key not in self.multi_parent_refs:
                self.multi_parent_refs[arango_key] = [first_path]
            self.multi_parent_refs[arango_key].append(path)
            
            return {
                'ref': first_path,
                'key': arango_key,
                'name': node.get('name', '')
            }
        
        # Первое посещение — полное описание
        self.visited[node_id] = path
        
        result = {
            'path': path,
            'key': arango_key,
            'name': node.get('name', ''),
            'type': node.get('kind', 'unknown'),
            'properties': self._extract_properties(node),
            'children': {}
        }
        
        # Добавить тип связи (если не корень)
        if edge_type:
            result['edge_type'] = edge_type
        
        # Обход дочерних узлов
        children = self.subgraph.get_children(node_id)
        for i, child_edge in enumerate(children):
            child_id = child_edge['to']
            child_num = i + 1
            child_path = self.numbering.make_path(path, child_num)
            
            result['children'][child_path] = self._traverse_recursive(
                child_id,
                child_path,
                edge_type=child_edge['type']
            )
        
        return result
    
    def _extract_properties(self, node: Dict) -> Dict:
        """
        Извлечь значимые свойства узла
        
        Исключает технические поля и пустые значения
        """
        exclude_keys = {'arango_key', 'name', 'kind', 'id'}
        
        props = {}
        for key, value in node.items():
            if key not in exclude_keys and value is not None and value != '' and value != []:
                props[key] = value
        
        return props
    
    def get_stats(self) -> Dict:
        """
        Получить статистику обхода
        
        Returns:
            Словарь со статистикой:
            - unique_nodes: количество уникальных узлов
            - multi_parent_nodes: узлы с множественными родителями
            - max_depth: максимальная глубина дерева
        """
        # Подсчитать максимальную глубину
        max_depth = 0
        for path in self.visited.values():
            depth = path.count('.') + 1
            max_depth = max(max_depth, depth)
        
        return {
            'unique_nodes': len(self.visited),
            'multi_parent_nodes': {
                key: len(paths) for key, paths in self.multi_parent_refs.items()
            },
            'max_depth': max_depth
        }
    
    def find_start_node(self, start_key: Optional[str] = None) -> int:
        """
        Найти стартовый узел для обхода
        
        Args:
            start_key: arango_key стартового узла (опционально)
            
        Returns:
            ID стартового узла
            
        Raises:
            ValueError: Если узел не найден
        """
        if start_key:
            # Пользователь указал конкретный узел
            node = self.subgraph.get_node_by_key(start_key)
            if not node:
                raise ValueError(f"Узел '{start_key}' не найден в подграфе")
            return node['id']
        
        # Автоматический поиск: сначала c:project
        project_node = self.subgraph.get_node_by_key('c:project')
        if project_node:
            return project_node['id']
        
        # Если c:project нет, найти корневой узел
        root_nodes = self.subgraph.find_root_nodes()
        if not root_nodes:
            raise ValueError("Не найден корневой узел в подграфе")
        
        return root_nodes[0]

