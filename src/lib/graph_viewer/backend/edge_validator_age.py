#!/usr/bin/env python3
"""
Модуль валидации рёбер графа для PostgreSQL + Apache AGE
Предотвращает создание дублирующих связей в обоих направлениях (A→B и B→A)
"""

from typing import Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import Json
import json


def format_properties_for_cypher(properties: Dict[str, Any]) -> str:
    """
    Форматировать свойства в Cypher синтаксис
    
    Args:
        properties: Словарь свойств
    
    Returns:
        str: Строка в Cypher формате, например: {relationType: "uses", projects: ["fepro"]}
    """
    if not properties:
        return "{}"
    
    parts = []
    for key, value in properties.items():
        if isinstance(value, str):
            # Строки в двойных кавычках
            parts.append(f'{key}: "{value}"')
        elif isinstance(value, list):
            # Массивы
            if value and isinstance(value[0], str):
                array_str = '[' + ', '.join(f'"{v}"' for v in value) + ']'
            else:
                array_str = json.dumps(value)
            parts.append(f'{key}: {array_str}')
        elif isinstance(value, (int, float, bool)):
            # Числа и boolean
            parts.append(f'{key}: {json.dumps(value)}')
        else:
            # Другие типы через JSON
            parts.append(f'{key}: {json.dumps(value)}')
    
    return '{' + ', '.join(parts) + '}'


class EdgeValidatorAGE:
    """Валидатор для проверки уникальности рёбер графа в Apache AGE"""
    
    def __init__(self, conn):
        """
        Инициализация валидатора
        
        Args:
            conn: Подключение к PostgreSQL базе данных (psycopg2 connection)
        """
        self.conn = conn
        self.graph_name = 'common_project_graph'
        self.edge_label = 'project_relation'
    
    def check_edge_uniqueness(
        self, 
        from_vertex_id: int, 
        to_vertex_id: int, 
        exclude_edge_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет уникальность связи между узлами в ОБОИХ направлениях
        
        Args:
            from_vertex_id: ID исходного узла в AGE (bigint)
            to_vertex_id: ID целевого узла
            exclude_edge_id: ID ребра для исключения из проверки (при обновлении)
        
        Returns:
            Tuple[bool, Optional[str]]: (is_unique, error_message)
                - is_unique: True если связь уникальна, False если дубликат
                - error_message: Сообщение об ошибке если найден дубликат
        """
        with self.conn.cursor() as cur:
            # Загрузить AGE
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Построить Cypher запрос для поиска дубликатов
            # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 не поддерживает параметры)
            if exclude_edge_id is None:
                # Без исключения (для создания нового ребра)
                query = f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    MATCH (a)-[e]->(b)
                    WHERE (id(a) = {from_vertex_id} AND id(b) = {to_vertex_id})
                       OR (id(a) = {to_vertex_id} AND id(b) = {from_vertex_id})
                    RETURN id(e) as edge_id, id(a) as from_id, id(b) as to_id
                    LIMIT 1
                $$) as (edge_id agtype, from_id agtype, to_id agtype)
                """
            else:
                # С исключением (для обновления)
                query = f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    MATCH (a)-[e]->(b)
                    WHERE ((id(a) = {from_vertex_id} AND id(b) = {to_vertex_id})
                        OR (id(a) = {to_vertex_id} AND id(b) = {from_vertex_id}))
                      AND id(e) <> {exclude_edge_id}
                    RETURN id(e) as edge_id, id(a) as from_id, id(b) as to_id
                    LIMIT 1
                $$) as (edge_id agtype, from_id agtype, to_id agtype)
                """
            
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                # Найден дубликат
                edge_id = int(str(result[0]).strip('"'))
                from_id = int(str(result[1]).strip('"'))
                
                # Определить направление
                if from_id == from_vertex_id:
                    direction = 'прямая'
                else:
                    direction = 'обратная'
                
                error_msg = (
                    f"Связь между вершинами {from_vertex_id} и {to_vertex_id} уже существует "
                    f"({direction} связь, ID: {edge_id})"
                )
                
                return False, error_msg
            
            return True, None
    
    def _add_projects_to_edge_table(self, edge_id: int, project_keys: list, created_by: str = 'api') -> int:
        """
        Добавить проекты к ребру в таблице edge_projects
        
        Args:
            edge_id: ID ребра
            project_keys: Список ключей проектов
            created_by: Кто создал связь
        
        Returns:
            int: Количество добавленных проектов
        """
        if not project_keys:
            return 0
        
        added_count = 0
        with self.conn.cursor() as cur:
            for project_key in project_keys:
                try:
                    cur.execute("""
                        SELECT ag_catalog.add_project_to_edge(
                            %s, %s, 'participant', 1.0, %s, 
                            jsonb_build_object('created_by', %s, 'created_via', 'edge_validator')
                        )
                    """, (edge_id, project_key, created_by, created_by))
                    if cur.fetchone()[0]:
                        added_count += 1
                except Exception as e:
                    # Логируем ошибку, но продолжаем
                    print(f"Предупреждение: не удалось добавить проект '{project_key}' к ребру {edge_id}: {e}")
        
        return added_count
    
    def _sync_projects_in_table(self, edge_id: int, project_keys: list, created_by: str = 'api'):
        """
        Синхронизировать проекты в таблице edge_projects
        
        Args:
            edge_id: ID ребра
            project_keys: Новый список ключей проектов
            created_by: Кто обновил связь
        """
        with self.conn.cursor() as cur:
            # Получить текущие проекты
            cur.execute("""
                SELECT p.key 
                FROM public.edge_projects ep
                JOIN public.projects p ON ep.project_id = p.id
                WHERE ep.edge_id = %s
            """, (edge_id,))
            current_projects = {row[0] for row in cur.fetchall()}
            new_projects = set(project_keys) if project_keys else set()
            
            # Удалить отсутствующие
            to_remove = current_projects - new_projects
            for project_key in to_remove:
                try:
                    cur.execute("""
                        SELECT ag_catalog.remove_project_from_edge(%s, %s)
                    """, (edge_id, project_key))
                except Exception as e:
                    print(f"Предупреждение: не удалось удалить проект '{project_key}' из ребра {edge_id}: {e}")
            
            # Добавить новые
            to_add = new_projects - current_projects
            self._add_projects_to_edge_table(edge_id, list(to_add), created_by)
    
    def insert_edge_safely(
        self, 
        from_vertex_id: int,
        to_vertex_id: int,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Безопасно вставляет ребро с проверкой уникальности
        Автоматически сохраняет projects в edge_projects таблицу
        
        Args:
            from_vertex_id: ID исходной вершины в AGE
            to_vertex_id: ID целевой вершины в AGE  
            properties: Свойства ребра (dict), например:
                {
                    'relationType': 'uses',
                    'projects': ['fepro', 'femsq']
                }
        
        Returns:
            Dict[str, Any]: Результат вставки с 'edge_id'
        
        Raises:
            ValueError: Если связь уже существует
        """
        # Извлечь projects из properties
        properties_copy = properties.copy()
        project_keys = properties_copy.pop('projects', [])
        
        # Проверить уникальность
        is_unique, error_msg = self.check_edge_uniqueness(from_vertex_id, to_vertex_id)
        
        if not is_unique:
            raise ValueError(error_msg)
        
        # Создать ребро через Cypher (БЕЗ projects в свойствах)
        # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 ограничение)
        with self.conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Конвертировать свойства в Cypher формат (без projects)
            props_str = format_properties_for_cypher(properties_copy)
            
            query = f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                MATCH (a), (b)
                WHERE id(a) = {from_vertex_id} AND id(b) = {to_vertex_id}
                CREATE (a)-[e:{self.edge_label} {props_str}]->(b)
                RETURN id(e) as edge_id
            $$) as (edge_id agtype)
            """
            
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                edge_id = int(str(result[0]).strip('"'))
                
                # Добавить проекты в edge_projects
                if project_keys:
                    self._add_projects_to_edge_table(edge_id, project_keys, 'api')
                
                self.conn.commit()
                
                # Вернуть результат с projects (для обратной совместимости)
                result_properties = properties_copy.copy()
                if project_keys:
                    result_properties['projects'] = project_keys
                
                return {
                    'edge_id': edge_id,
                    'from': from_vertex_id,
                    'to': to_vertex_id,
                    **result_properties
                }
            else:
                raise RuntimeError("Не удалось создать ребро")
    
    def update_edge_safely(
        self,
        edge_id: int,
        new_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Безопасно обновляет свойства ребра
        Автоматически синхронизирует projects в edge_projects таблице
        
        Args:
            edge_id: ID ребра в AGE (bigint)
            new_properties: Новые свойства ребра (может содержать 'projects')
        
        Returns:
            Dict[str, Any]: Результат обновления
        
        Raises:
            ValueError: Если обновление создаст дубликат (для изменения узлов)
            RuntimeError: Если ребро не найдено
        """
        # Извлечь projects из new_properties
        properties_copy = new_properties.copy()
        project_keys = properties_copy.pop('projects', None)  # None означает "не обновлять"
        
        with self.conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Обновить свойства ребра (БЕЗ projects, если они были указаны)
            # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 ограничение)
            # Используем += для слияния свойств (сохранение существующих полей)
            if properties_copy:  # Обновлять только если есть изменения
                props_str = format_properties_for_cypher(properties_copy)
                
                query = f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    MATCH ()-[e]->()
                    WHERE id(e) = {edge_id}
                    SET e += {props_str}
                    RETURN id(e) as edge_id
                $$) as (edge_id agtype)
                """
                
                cur.execute(query)
                result = cur.fetchone()
                
                if not result or not result[0]:
                    raise RuntimeError(f"Ребро с ID {edge_id} не найдено")
            
            # Синхронизировать projects в edge_projects (если указаны)
            if project_keys is not None:  # None означает "не обновлять"
                self._sync_projects_in_table(edge_id, project_keys, 'api')
            
            self.conn.commit()
            
            # Вернуть результат с актуальными projects
            result_properties = properties_copy.copy() if properties_copy else {}
            if project_keys is not None:
                result_properties['projects'] = project_keys
            
            return {'edge_id': edge_id, **result_properties}
    
    def delete_edge(self, edge_id: int) -> bool:
        """
        Удаляет ребро по ID
        Автоматически удаляет связанные записи из edge_projects (каскадно через ON DELETE CASCADE)
        
        Args:
            edge_id: ID ребра в AGE (bigint)
        
        Returns:
            bool: True если успешно удалено
        
        Raises:
            RuntimeError: Если ребро не найдено
        """
        with self.conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Удалить из edge_projects вручную (для явности, хотя есть ON DELETE CASCADE)
            cur.execute("DELETE FROM public.edge_projects WHERE edge_id = %s", (edge_id,))
            
            # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 ограничение)
            query = f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                MATCH ()-[e]->()
                WHERE id(e) = {edge_id}
                DELETE e
                RETURN id(e) as edge_id
            $$) as (edge_id agtype)
            """
            
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                self.conn.commit()
                return True
            else:
                self.conn.rollback()
                raise RuntimeError(f"Ребро с ID {edge_id} не найдено")


# Вспомогательная функция для создания валидатора
def create_edge_validator(conn) -> EdgeValidatorAGE:
    """
    Создать экземпляр валидатора рёбер для AGE
    
    Args:
        conn: Подключение к PostgreSQL с AGE
    
    Returns:
        EdgeValidatorAGE: Экземпляр валидатора
    """
    return EdgeValidatorAGE(conn)

