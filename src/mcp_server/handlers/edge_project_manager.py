#!/usr/bin/env python3
"""
Edge Project Manager Handler для MCP сервера
Предоставляет команды для работы с проектами рёбер графа через API
"""

import requests
from typing import Optional, List, Dict, Any


class EdgeProjectManagerHandler:
    """Handler для управления проектами рёбер графа через API"""
    
    def __init__(self, api_url: str = "http://localhost:15000"):
        """
        Инициализация handler'а
        
        Args:
            api_url: URL API сервера Graph Viewer (default: 15000)
        """
        self.api_url = api_url.rstrip('/')
    
    def get_projects(self, edge_id: int) -> Dict[str, Any]:
        """
        Получить список проектов, связанных с ребром
        
        Args:
            edge_id: ID ребра (число)
        
        Returns:
            Dict с результатом операции:
            {
                'success': bool,
                'edge_id': int,
                'projects': list  # список проектов с информацией
            }
        """
        try:
            response = requests.get(
                f'{self.api_url}/api/edges/{edge_id}/projects',
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def add_project(
        self,
        edge_id: int,
        project_key: str,
        role: str = 'participant',
        weight: float = 1.0,
        created_by: str = 'api',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Добавить проект к ребру
        
        Args:
            edge_id: ID ребра
            project_key: Ключ проекта (fepro, femsq, fedoc)
            role: Роль проекта в связи (default: 'participant')
            weight: Вес связи (default: 1.0)
            created_by: Кто создал связь (default: 'api')
            metadata: Дополнительные метаданные (optional)
        
        Returns:
            Dict с результатом операции
        """
        try:
            data = {
                'project_key': project_key,
                'role': role,
                'weight': weight,
                'created_by': created_by
            }
            
            if metadata:
                data['metadata'] = metadata
            
            response = requests.post(
                f'{self.api_url}/api/edges/{edge_id}/projects',
                json=data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def remove_project(self, edge_id: int, project_key: str) -> Dict[str, Any]:
        """
        Удалить проект из ребра
        
        Args:
            edge_id: ID ребра
            project_key: Ключ проекта для удаления
        
        Returns:
            Dict с результатом операции
        """
        try:
            response = requests.delete(
                f'{self.api_url}/api/edges/{edge_id}/projects/{project_key}',
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def get_edge_info(self, edge_id: int) -> Dict[str, Any]:
        """
        Получить полную информацию о ребре (узлы, тип связи, проекты)
        
        Args:
            edge_id: ID ребра
        
        Returns:
            Dict с полной информацией о ребре
        """
        try:
            response = requests.get(
                f'{self.api_url}/api/edges/{edge_id}',
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def check_connection(
        self,
        from_node: str,
        to_node: str,
        project_filter: Optional[str] = None,
        mode: str = 'direct',
        direction: str = 'outbound',
        time_limit_ms: Optional[int] = None,
        hard_kill_ms: Optional[int] = None,
        enumerate_nodes_only: bool = True,
        return_partial: bool = True
    ) -> Dict[str, Any]:
        """
        Проверить наличие связи между узлами с детальной информацией
        
        Args:
            from_node: ID или ключ исходного узла
            to_node: ID или ключ целевого узла
            project_filter: Фильтр по проекту (optional)
        
        Returns:
            Dict с результатом проверки:
            {
                'connected': bool,
                'edge': dict (если связь найдена),
                'for_project': dict (статус для каждого проекта)
            }
        """
        try:
            data = {
                'from_node': from_node,
                'to_node': to_node,
                'mode': mode,
                'direction': direction,
                'enumerate_nodes_only': enumerate_nodes_only,
                'return_partial': return_partial
            }
            
            if project_filter:
                data['project_filter'] = project_filter
            if time_limit_ms is not None:
                data['time_limit_ms'] = int(time_limit_ms)
            if hard_kill_ms is not None:
                data['hard_kill_ms'] = int(hard_kill_ms)
            
            response = requests.post(
                f'{self.api_url}/api/edges/check-connection',
                json=data,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def batch_add_projects(
        self,
        edge_ids: List[int],
        project_key: str,
        role: str = 'participant',
        weight: float = 1.0,
        created_by: str = 'api',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Массовое добавление проекта к нескольким рёбрам
        
        Args:
            edge_ids: Массив ID рёбер
            project_key: Ключ проекта
            role: Роль проекта (default: 'participant')
            weight: Вес связи (default: 1.0)
            created_by: Кто создал связь (default: 'api')
            metadata: Дополнительные метаданные (optional)
        
        Returns:
            Dict с результатом операции и статистикой
        """
        try:
            data = {
                'edge_ids': edge_ids,
                'project_key': project_key,
                'role': role,
                'weight': weight,
                'created_by': created_by
            }
            
            if metadata:
                data['metadata'] = metadata
            
            response = requests.post(
                f'{self.api_url}/api/edges/batch-add-projects',
                json=data,
                timeout=30  # Больше времени для массовых операций
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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
    
    def batch_remove_projects(
        self,
        edge_ids: List[int],
        project_key: str
    ) -> Dict[str, Any]:
        """
        Массовое удаление проекта из нескольких рёбер
        
        Args:
            edge_ids: Массив ID рёбер
            project_key: Ключ проекта для удаления
        
        Returns:
            Dict с результатом операции и статистикой
        """
        try:
            data = {
                'edge_ids': edge_ids,
                'project_key': project_key
            }
            
            response = requests.post(
                f'{self.api_url}/api/edges/batch-remove-projects',
                json=data,
                timeout=30  # Больше времени для массовых операций
            )
            
            result = response.json()
            
            if response.status_code == 200:
                return result
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


def create_edge_project_manager_handler(api_url: str = "http://localhost:15000") -> EdgeProjectManagerHandler:
    """
    Создать экземпляр Edge Project Manager Handler
    
    Args:
        api_url: URL API сервера (default: 15000)
    
    Returns:
        EdgeProjectManagerHandler: Экземпляр handler'а
    """
    return EdgeProjectManagerHandler(api_url)

