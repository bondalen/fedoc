#!/usr/bin/env python3
"""
Модуль валидации рёбер графа
Предотвращает создание дублирующих связей в обоих направлениях (A→B и B→A)
"""

from typing import Dict, Any, Optional, Tuple


class EdgeValidator:
    """Валидатор для проверки уникальности рёбер графа"""
    
    def __init__(self, db):
        """
        Инициализация валидатора
        
        Args:
            db: Подключение к ArangoDB базе данных
        """
        self.db = db
        self.edges_collection = 'project_relations'
    
    def check_edge_uniqueness(
        self, 
        from_node: str, 
        to_node: str, 
        exclude_edge_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет уникальность связи между узлами в ОБОИХ направлениях
        
        Args:
            from_node: ID исходного узла (например, 'canonical_nodes/c:backend')
            to_node: ID целевого узла
            exclude_edge_id: ID ребра для исключения из проверки (при обновлении)
        
        Returns:
            Tuple[bool, Optional[str]]: (is_unique, error_message)
                - is_unique: True если связь уникальна, False если дубликат
                - error_message: Сообщение об ошибке если найден дубликат
        """
        # Построить AQL запрос
        query = """
        FOR e IN @@collection
            FILTER (e._from == @from AND e._to == @to) 
                OR (e._from == @to AND e._to == @from)
        """
        
        bind_vars = {
            '@collection': self.edges_collection,
            'from': from_node,
            'to': to_node
        }
        
        # Исключить текущее ребро при обновлении
        if exclude_edge_id:
            query += " FILTER e._id != @exclude_id"
            bind_vars['exclude_id'] = exclude_edge_id
        
        query += " LIMIT 1 RETURN {_id: e._id, _from: e._from, _to: e._to}"
        
        # Выполнить запрос
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        existing_edges = list(cursor)
        
        if existing_edges:
            edge = existing_edges[0]
            from_label = from_node.split('/')[-1] if '/' in from_node else from_node
            to_label = to_node.split('/')[-1] if '/' in to_node else to_node
            
            # Определить направление дубликата
            if edge['_from'] == from_node:
                direction = 'прямая'
                existing_from = edge['_from'].split('/')[-1]
                existing_to = edge['_to'].split('/')[-1]
            else:
                direction = 'обратная'
                existing_from = edge['_to'].split('/')[-1]
                existing_to = edge['_from'].split('/')[-1]
            
            error_msg = (
                f"Связь между узлами '{from_label}' и '{to_label}' уже существует "
                f"({direction} связь: {existing_from} → {existing_to}, ID: {edge['_id']})"
            )
            
            return False, error_msg
        
        return True, None
    
    def insert_edge_safely(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Безопасно вставляет ребро с проверкой уникальности
        
        Args:
            edge_data: Данные ребра, должны содержать '_from' и '_to'
                Пример: {
                    '_from': 'canonical_nodes/c:backend',
                    '_to': 'canonical_nodes/t:java@21',
                    'relationType': 'uses',
                    'projects': ['fepro', 'femsq']
                }
        
        Returns:
            Dict[str, Any]: Результат вставки с '_id', '_key', '_rev'
        
        Raises:
            ValueError: Если связь уже существует
            KeyError: Если отсутствуют обязательные поля '_from' или '_to'
        """
        # Проверить обязательные поля
        if '_from' not in edge_data:
            raise KeyError("Отсутствует обязательное поле '_from'")
        if '_to' not in edge_data:
            raise KeyError("Отсутствует обязательное поле '_to'")
        
        from_node = edge_data['_from']
        to_node = edge_data['_to']
        
        # Проверить уникальность
        is_unique, error_msg = self.check_edge_uniqueness(from_node, to_node)
        
        if not is_unique:
            raise ValueError(error_msg)
        
        # Вставить ребро
        collection = self.db.collection(self.edges_collection)
        result = collection.insert(edge_data)
        
        return result
    
    def update_edge_safely(
        self, 
        edge_id: str, 
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Безопасно обновляет ребро с проверкой уникальности
        
        Args:
            edge_id: ID ребра для обновления (например, 'project_relations/12345')
            new_data: Новые данные ребра
        
        Returns:
            Dict[str, Any]: Результат обновления
        
        Raises:
            ValueError: Если новая связь создаст дубликат
            KeyError: Если ребро не найдено
        """
        collection = self.db.collection(self.edges_collection)
        
        # Извлечь ключ из полного ID (project_relations/12345 -> 12345)
        if '/' in edge_id:
            edge_key = edge_id.split('/', 1)[1]
        else:
            edge_key = edge_id
        
        # Получить текущее ребро
        try:
            current_edge = collection.get(edge_key)
            if not current_edge:
                raise KeyError(f"Ребро с ID '{edge_id}' не найдено")
        except Exception as e:
            raise KeyError(f"Ребро с ID '{edge_id}' не найдено: {e}")
        
        # Определить новые узлы (если они изменились)
        new_from = new_data.get('_from', current_edge['_from'])
        new_to = new_data.get('_to', current_edge['_to'])
        
        # Проверить уникальность, исключая текущее ребро
        # Используем полный ID для exclude_edge_id
        full_edge_id = f"{self.edges_collection}/{edge_key}" if '/' not in edge_id else edge_id
        is_unique, error_msg = self.check_edge_uniqueness(
            new_from, 
            new_to, 
            exclude_edge_id=full_edge_id
        )
        
        if not is_unique:
            raise ValueError(error_msg)
        
        # Обновить ребро (передаем словарь с _key)
        result = collection.update({'_key': edge_key}, new_data)
        
        return result
    
    def delete_edge(self, edge_id: str) -> bool:
        """
        Удаляет ребро по ID
        
        Args:
            edge_id: ID ребра для удаления (например, 'project_relations/12345')
        
        Returns:
            bool: True если успешно удалено
        
        Raises:
            KeyError: Если ребро не найдено
        """
        collection = self.db.collection(self.edges_collection)
        
        # Извлечь ключ из полного ID (project_relations/12345 -> 12345)
        if '/' in edge_id:
            edge_key = edge_id.split('/', 1)[1]
        else:
            edge_key = edge_id
        
        try:
            collection.delete(edge_key)
            return True
        except Exception as e:
            raise KeyError(f"Ошибка при удалении ребра '{edge_id}': {e}")


# Вспомогательная функция для создания валидатора
def create_edge_validator(db) -> EdgeValidator:
    """
    Создать экземпляр валидатора рёбер
    
    Args:
        db: Подключение к ArangoDB
    
    Returns:
        EdgeValidator: Экземпляр валидатора
    """
    return EdgeValidator(db)


