#!/usr/bin/env python3
"""
Edge Manager Handler для MCP сервера
Предоставляет команды для работы со связями графа с валидацией уникальности
"""

import requests
import json
from typing import Optional, List, Dict, Any


class EdgeManagerHandler:
    """Handler для управления рёбрами графа через API"""
    
    def __init__(self, api_url: str = "http://localhost:8899"):
        """
        Инициализация handler'а
        
        Args:
            api_url: URL API сервера Graph Viewer
        """
        self.api_url = api_url.rstrip('/')
    
    def add_edge(
        self, 
        from_node: str, 
        to_node: str, 
        relation_type: str = "related",
        projects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Добавить новое ребро между узлами с валидацией уникальности
        
        Args:
            from_node: ID исходного узла (например 'canonical_nodes/c:backend')
            to_node: ID целевого узла
            relation_type: Тип связи (по умолчанию 'related')
            projects: Список проектов, использующих эту связь
        
        Returns:
            Dict с результатом операции:
            {
                'success': bool,
                'edge': dict,  # если успешно
                'error': str   # если ошибка
            }
        """
        try:
            edge_data = {
                '_from': from_node,
                '_to': to_node,
                'relationType': relation_type,
                'projects': projects or []
            }
            
            response = requests.post(
                f'{self.api_url}/api/edges',
                json=edge_data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'edge': result.get('edge', {}),
                    'message': f"✅ Связь создана: {result['edge']['_id']}"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Неизвестная ошибка'),
                    'status_code': response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка подключения к API: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {e}'
            }
    
    def update_edge(
        self, 
        edge_id: str, 
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        relation_type: Optional[str] = None,
        projects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Обновить существующее ребро с валидацией уникальности
        
        Args:
            edge_id: ID ребра (например 'project_relations/12345')
            from_node: Новый исходный узел (optional)
            to_node: Новый целевой узел (optional)
            relation_type: Новый тип связи (optional)
            projects: Новый список проектов (optional)
        
        Returns:
            Dict с результатом операции
        """
        try:
            update_data = {}
            
            if from_node:
                update_data['_from'] = from_node
            if to_node:
                update_data['_to'] = to_node
            if relation_type:
                update_data['relationType'] = relation_type
            if projects is not None:
                update_data['projects'] = projects
            
            if not update_data:
                return {
                    'success': False,
                    'error': 'Не указано ни одного поля для обновления'
                }
            
            response = requests.put(
                f'{self.api_url}/api/edges/{edge_id}',
                json=update_data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'edge': result.get('edge', {}),
                    'message': f"✅ Связь обновлена: {edge_id}"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Неизвестная ошибка'),
                    'status_code': response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка подключения к API: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {e}'
            }
    
    def delete_edge(self, edge_id: str) -> Dict[str, Any]:
        """
        Удалить ребро
        
        Args:
            edge_id: ID ребра (например 'project_relations/12345')
        
        Returns:
            Dict с результатом операции
        """
        try:
            response = requests.delete(
                f'{self.api_url}/api/edges/{edge_id}',
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f"✅ Связь удалена: {edge_id}"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Неизвестная ошибка'),
                    'status_code': response.status_code
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка подключения к API: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {e}'
            }
    
    def check_edge_uniqueness(
        self, 
        from_node: str, 
        to_node: str,
        exclude_edge_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверить уникальность связи между узлами
        
        Args:
            from_node: ID исходного узла
            to_node: ID целевого узла
            exclude_edge_id: ID ребра для исключения из проверки (optional)
        
        Returns:
            Dict с результатом проверки:
            {
                'is_unique': bool,
                'error': str (если не уникальна)
            }
        """
        try:
            check_data = {
                '_from': from_node,
                '_to': to_node
            }
            
            if exclude_edge_id:
                check_data['exclude_edge_id'] = exclude_edge_id
            
            response = requests.post(
                f'{self.api_url}/api/edges/check',
                json=check_data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                is_unique = result.get('is_unique', False)
                error = result.get('error')
                
                if is_unique:
                    return {
                        'is_unique': True,
                        'message': "✅ Связь уникальна"
                    }
                else:
                    return {
                        'is_unique': False,
                        'error': error or 'Связь уже существует'
                    }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Ошибка проверки')
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка подключения к API: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {e}'
            }


def create_edge_manager_handler(api_url: str = "http://localhost:8899") -> EdgeManagerHandler:
    """
    Создать экземпляр Edge Manager Handler
    
    Args:
        api_url: URL API сервера
    
    Returns:
        EdgeManagerHandler: Экземпляр handler'а
    """
    return EdgeManagerHandler(api_url)


