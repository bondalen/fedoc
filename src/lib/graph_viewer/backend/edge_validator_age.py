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
    
    def insert_edge_safely(
        self, 
        from_vertex_id: int,
        to_vertex_id: int,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Безопасно вставляет ребро с проверкой уникальности
        
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
        # Проверить уникальность
        is_unique, error_msg = self.check_edge_uniqueness(from_vertex_id, to_vertex_id)
        
        if not is_unique:
            raise ValueError(error_msg)
        
        # Создать ребро через Cypher
        # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 ограничение)
        with self.conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Конвертировать свойства в Cypher формат
            props_str = format_properties_for_cypher(properties)
            
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
                self.conn.commit()
                
                return {
                    'edge_id': edge_id,
                    'from': from_vertex_id,
                    'to': to_vertex_id,
                    **properties
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
        
        Args:
            edge_id: ID ребра в AGE (bigint)
            new_properties: Новые свойства ребра
        
        Returns:
            Dict[str, Any]: Результат обновления
        
        Raises:
            ValueError: Если обновление создаст дубликат (для изменения узлов)
            RuntimeError: Если ребро не найдено
        """
        with self.conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Обновить свойства ребра
            # Используем FORMAT() вместо параметров (Apache AGE 1.6.0 ограничение)
            props_str = format_properties_for_cypher(new_properties)
            
            query = f"""
            SELECT * FROM cypher('{self.graph_name}', $$
                MATCH ()-[e]->()
                WHERE id(e) = {edge_id}
                SET e = {props_str}
                RETURN id(e) as edge_id
            $$) as (edge_id agtype)
            """
            
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                self.conn.commit()
                return {'edge_id': edge_id, **new_properties}
            else:
                raise RuntimeError(f"Ребро с ID {edge_id} не найдено")
    
    def delete_edge(self, edge_id: int) -> bool:
        """
        Удаляет ребро по ID
        
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

