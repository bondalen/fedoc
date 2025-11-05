#!/usr/bin/env python3
"""
API сервер для graph viewer frontend (PostgreSQL + Apache AGE версия)
Предоставляет REST API endpoints и WebSocket для фронтенд-приложения

Версия 3.0 с поддержкой Apache AGE вместо ArangoDB
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2 import IntegrityError
import argparse
import sys
import json
import time
import threading
import os
from pathlib import Path
from typing import Optional

# Добавить путь к модулям для импорта
sys.path.insert(0, str(Path(__file__).parent))

# Импорт валидатора рёбер для AGE
from edge_validator_age import create_edge_validator
from project_enricher import enrich_object_properties

# Перенаправление print в stderr для MCP протокола
def log(message):
    """Вывод в stderr чтобы не нарушать MCP протокол"""
    print(message, file=sys.stderr, flush=True)

# Создание Flask приложения
app = Flask(__name__)
CORS(app)  # Разрешить CORS для всех доменов

# Создание SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Глобальные переменные
db_conn = None  # PostgreSQL connection
edge_validator = None  # Валидатор рёбер
graph_name = 'common_project_graph'
_selection_response = None  # Последний ответ от браузера
_selection_lock = threading.Lock()  # Блокировка для thread-safe доступа


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def execute_cypher(query: str, params: dict = None, return_type: str = 'auto'):
    """
    Выполнить Cypher запрос к Apache AGE
    
    Args:
        query: Cypher запрос (без оберток cypher())
        params: Параметры запроса
        return_type: Тип возвращаемых данных ('auto', 'node', 'edge', 'graph', 'list')
    
    Returns:
        list: Список результатов
    """
    with db_conn.cursor() as cur:
        # Загрузить AGE и установить search_path
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Обернуть в cypher() вызов с правильной структурой
        if params:
            # Заменить параметры в запросе напрямую
            for key, value in params.items():
                if isinstance(value, str):
                    query = query.replace(f'${key}', f"'{value}'")
                else:
                    query = query.replace(f'${key}', str(value))
        
        # Определить количество возвращаемых колонок
        if return_type == 'auto':
            # Автоопределение по запросу
            if "edge_id" in query and "from_id" in query:
                return_type = 'graph'
            elif "RETURN n" in query or "RETURN r" in query:
                return_type = 'node'
            else:
                return_type = 'list'
        
        # Выбрать определение колонок
        if return_type == 'graph':
            # Запрос для графа - много колонок
            full_query = f"SELECT * FROM cypher('{graph_name}', $${query}$$) as (edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype, from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, projects agtype, rel_type agtype)"
        elif return_type == 'node' or return_type == 'edge':
            # Запрос возвращает целый узел/ребро
            full_query = f"SELECT * FROM cypher('{graph_name}', $${query}$$) as (result agtype)"
        else:
            # Запрос для списка узлов - 3 колонки
            full_query = f"SELECT * FROM cypher('{graph_name}', $${query}$$) as (id agtype, key agtype, name agtype)"
        
        cur.execute(full_query)
        
        return cur.fetchall()


def execute_sql_function(function_name: str, *args):
    """
    Выполнить PostgreSQL функцию
    
    Args:
        function_name: Имя функции в формате 'schema.function_name'
        *args: Аргументы функции
    
    Returns:
        list: Список результатов
    """
    with db_conn.cursor() as cur:
        # Загрузить AGE и установить search_path
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Сформировать список параметров
        params_list = []
        for arg in args:
            if arg is None:
                params_list.append('NULL')
            elif isinstance(arg, str):
                # Экранировать одинарные кавычки
                escaped = arg.replace("'", "''")
                params_list.append(f"'{escaped}'")
            elif isinstance(arg, (int, float)):
                params_list.append(str(arg))
            else:
                params_list.append(str(arg))
        
        params_str = ', '.join(params_list)
        query = f"SELECT * FROM {function_name}({params_str})"
        
        cur.execute(query)
        return cur.fetchall()


def agtype_to_python(agtype_value):
    """
    Конвертировать agtype в Python объект
    
    Args:
        agtype_value: Значение типа agtype
    
    Returns:
        Сконвертированное значение
    """
    if agtype_value is None:
        return None
    
    # Агтип возвращается как строка, парсим её
    s = str(agtype_value)
    
    # Убрать суффиксы ::vertex, ::edge, ::path если есть
    if '::' in s:
        s = s.split('::')[0]
    
    # Убрать кавычки если это строка
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    
    # Попробовать распарсить как JSON
    try:
        parsed = json.loads(s)
        # Если это объект с полем _id, извлечь его
        if isinstance(parsed, dict) and '_id' in parsed:
            return parsed['_id']
        return parsed
    except json.JSONDecodeError:
        # Если не JSON, попробовать как число
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s
    except Exception:
        return s


def convert_node_key_to_age_id(node_identifier: str) -> Optional[int]:
    """
    Конвертировать arango-style ключ в AGE vertex ID
    
    Args:
        node_identifier: ID или ключ узла:
            - "canonical_nodes/c:backend" (arango-style ID)
            - "c:backend" (arango key)
            - "844424930131969" (уже AGE ID)
    
    Returns:
        int: AGE vertex ID или None если не найден
    
    Raises:
        ValueError: Если узел не найден
    """
    # Попробовать распарсить как число (уже AGE ID)
    try:
        return int(node_identifier)
    except ValueError:
        pass
    
    # Извлечь ключ из arango-style ID
    # Если содержит '/', это может быть arango-style ID (collection/key) или путь с '/' (например d:src/lib)
    # Если начинается с префикса (c:, t:, v:, d:, m:, f:), используем как есть (это уже ключ)
    if node_identifier.startswith(('c:', 't:', 'v:', 'd:', 'm:', 'f:')):
        key = node_identifier
    else:
        # Иначе извлекаем последнюю часть после '/'
        key = node_identifier.split('/')[-1] if '/' in node_identifier else node_identifier
    
    # Запрос к PostgreSQL для получения AGE ID по ключу
    with db_conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Используем параметризованный запрос через FORMAT для безопасности
        query = f"""
            SELECT * FROM cypher('common_project_graph', $$
                MATCH (n:canonical_node {{arango_key: '{key}'}})
                RETURN id(n)
            $$) AS (node_id agtype);
        """
        
        try:
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                age_id = agtype_to_python(result[0])
                return int(age_id)
            else:
                raise ValueError(f"Узел с ключом '{key}' не найден в графе")
                
        except Exception as e:
            raise ValueError(f"Ошибка поиска узла '{key}': {e}")


def convert_edge_key_to_age_id(edge_identifier: str) -> Optional[int]:
    """
    Конвертировать arango-style ключ ребра в AGE edge ID
    
    Args:
        edge_identifier: ID или ключ ребра:
            - "project_relations/12345" (arango-style ID)
            - "12345" (arango key)
            - "1125899906842625" (уже AGE ID)
    
    Returns:
        int: AGE edge ID или None если не найден
    
    Raises:
        ValueError: Если ребро не найдено
    """
    # Попробовать распарсить как число (уже AGE ID)
    try:
        return int(edge_identifier)
    except ValueError:
        pass
    
    # Извлечь ключ из arango-style ID
    key = edge_identifier.split('/')[-1] if '/' in edge_identifier else edge_identifier
    
    # Для рёбер пока просто пробуем как число
    try:
        return int(key)
    except ValueError:
        raise ValueError(f"Не удалось конвертировать ID ребра: {edge_identifier}")


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def process_edge(edge_id, from_id, to_id, from_name, to_name, from_key, to_key, 
                from_kind, to_kind, projects, rel_type, project, theme, nodes_map, edges_map):
    """Обработать ребро и добавить связанные узлы"""
    # Определяем тип узла по ключу (как в process_isolated_node)
    def get_node_kind(key):
        if key.startswith('c:'):
            return 'concept'
        elif key.startswith('t:'):
            return 'technology'
        elif key.startswith('v:'):
            return 'version'
        else:
            return 'other'
    
    # Добавить узлы (всегда, независимо от фильтрации проекта)
    if from_id not in nodes_map:
        from_node_kind = get_node_kind(from_key)
        nodes_map[from_id] = {
            'id': from_id,
            'label': from_name,
            '_key': from_key,
            'shape': 'box' if from_node_kind == 'concept' else 'ellipse',
            'color': {
                'background': '#263238' if theme == 'dark' else '#E3F2FD'
            } if from_node_kind == 'concept' else {
                'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
            }
        }
    
    if to_id not in nodes_map:
        to_node_kind = get_node_kind(to_key)
        nodes_map[to_id] = {
            'id': to_id,
            'label': to_name,
            '_key': to_key,
            'shape': 'box' if to_node_kind == 'concept' else 'ellipse',
            'color': {
                'background': '#263238' if theme == 'dark' else '#E3F2FD'
            } if to_node_kind == 'concept' else {
                'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
            }
        }
    
    # Добавить ребро с проверкой правильного направления
    # Фильтрация по проекту для рёбер
    if project and (not projects or project not in projects):
        return
    
    if edge_id not in edges_map:
        # Использовать данные как есть (PostgreSQL функция исправлена)
        actual_from = from_id
        actual_to = to_id
        
        edges_map[edge_id] = {
            'id': edge_id,
            'from': actual_from,
            'to': actual_to,
            'label': ', '.join(projects) if projects else 'альтернатива',
            'color': {
                'color': '#64B5F6' if projects else '#9E9E9E'
            }
        }

def process_isolated_node(node_id, node_key, node_name, theme, nodes_map):
    """Обработать изолированный узел"""
    if node_id not in nodes_map:
        # Определяем тип узла по ключу
        if node_key.startswith('c:'):
            node_kind = 'concept'
        elif node_key.startswith('t:'):
            node_kind = 'technology'
        elif node_key.startswith('v:'):
            node_kind = 'version'
        else:
            node_kind = 'other'
        
        nodes_map[node_id] = {
            'id': node_id,
            'label': node_name,
            '_key': node_key,
            'shape': 'box' if node_kind == 'concept' else 'ellipse',
            'color': {
                'background': '#263238' if theme == 'dark' else '#E3F2FD'
            } if node_kind == 'concept' else {
                'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
            }
        }

# ========== REST API ENDPOINTS ==========

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Вернуть список узлов используя PostgreSQL функции"""
    try:
        project = request.args.get('project', '')
        
        # Используем новую PostgreSQL функцию
        results = execute_sql_function('ag_catalog.get_all_nodes_for_viewer', project if project else None)
        
        # Конвертировать результаты
        nodes = []
        for row in results:
            nodes.append({
                '_id': agtype_to_python(row[0]),
                '_key': agtype_to_python(row[1]),
                'name': agtype_to_python(row[2])
            })
        
        return jsonify(nodes)
    except Exception as e:
        log(f"Error in get_nodes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes', methods=['POST'])
def create_node():
    """Создать новый узел в графе"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Пустой запрос'}), 400
        
        node_key = data.get('node_key')
        node_name = data.get('node_name')
        node_type = data.get('node_type')
        properties = data.get('properties', {})
        
        # Валидация обязательных полей
        if not all([node_key, node_name, node_type]):
            return jsonify({'error': 'Отсутствуют обязательные поля: node_key, node_name, node_type'}), 400
        
        # Валидация типа узла
        valid_types = ['concept', 'technology', 'version', 'directory', 'module', 'other']
        if node_type not in valid_types:
            return jsonify({'error': f'Некорректный тип узла. Допустимые: {", ".join(valid_types)}'}), 400
        
        # Валидация ключа узла
        if not validate_node_key(node_key, node_type):
            return jsonify({'error': f'Некорректный формат ключа для типа "{node_type}". Ожидается префикс: {get_expected_prefix(node_type)}'}), 400
        
        # Проверка уникальности ключа
        if check_node_key_exists(node_key):
            return jsonify({'error': f'Узел с ключом "{node_key}" уже существует'}), 409
        
        # Создание узла в базе данных
        try:
            node_id = create_node_in_db(node_key, node_name, node_type, properties)
        except IntegrityError as e:
            if 'Узел с ключом' in str(e):
                return jsonify({'error': str(e)}), 409
            else:
                return jsonify({'error': f'Ошибка целостности данных: {str(e)}'}), 409
        
        log(f"✓ Node created: {node_id} ({node_key})")
        
        return jsonify({
            'success': True,
            'message': f'Узел {node_key} ({node_name}) успешно создан',
            'node_id': node_id,
            'node_key': node_key,
            'node_name': node_name,
            'node_type': node_type
        })
        
    except Exception as e:
        log(f"✗ Error creating node: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    """Обновить существующий узел в графе"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Пустой запрос'}), 400
        
        node_name = data.get('node_name')
        node_type = data.get('node_type')
        properties = data.get('properties', {})
        
        # Проверяем, что есть что обновлять
        if not any([node_name, node_type, properties]):
            return jsonify({'error': 'Не указаны поля для обновления'}), 400
        
        # Проверяем существование узла
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            node_query = f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (n) WHERE id(n) = {node_id}
                    RETURN n.arango_key, n.name, n.node_type
                $$) AS (key agtype, name agtype, node_type agtype);
            """
            cur.execute(node_query)
            node_result = cur.fetchone()
            
            if not node_result:
                return jsonify({'error': f'Узел с ID {node_id} не найден'}), 404
            
            current_key = agtype_to_python(node_result[0])
            current_name = agtype_to_python(node_result[1])
            current_type = agtype_to_python(node_result[2])
        
        # Валидация типа узла
        if node_type:
            valid_types = ['concept', 'technology', 'version', 'directory', 'module', 'other']
            if node_type not in valid_types:
                return jsonify({'error': f'Некорректный тип узла. Допустимые: {", ".join(valid_types)}'}), 400
        
        # Подготавливаем обновления
        updates = []
        if node_name:
            updates.append(f"n.name = '{node_name}'")
        if node_type:
            updates.append(f"n.node_type = '{node_type}'")
        if properties:
            props_list = []
            for key, value in properties.items():
                if isinstance(value, str):
                    props_list.append(f"{key}: '{value}'")
                else:
                    props_list.append(f"{key}: {value}")
            extra_props = ", ".join(props_list)
            updates.append(f"n += {{{extra_props}}}")
        
        if not updates:
            return jsonify({'error': 'Нет полей для обновления'}), 400
        
        # Выполняем обновление
        update_query = f"""
            SELECT * FROM cypher('{graph_name}', $$
                MATCH (n) WHERE id(n) = {node_id}
                SET {', '.join(updates)}
                RETURN n.arango_key, n.name, n.node_type, id(n)
            $$) AS (key agtype, name agtype, node_type agtype, node_id agtype);
        """
        
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute(update_query)
            result = cur.fetchone()
            
            if not result:
                return jsonify({'error': 'Не удалось обновить узел'}), 500
            
            updated_key = agtype_to_python(result[0])
            updated_name = agtype_to_python(result[1])
            updated_type = agtype_to_python(result[2])
            updated_id = agtype_to_python(result[3])
        
        log(f"✓ Node updated: {updated_id} ({updated_key})")
        
        return jsonify({
            'success': True,
            'message': f'Узел {updated_key} успешно обновлен',
            'node_id': updated_id,
            'node_key': updated_key,
            'node_name': updated_name,
            'node_type': updated_type
        })
        
    except Exception as e:
        log(f"✗ Error updating node {node_id}: {e}")
        return jsonify({'error': str(e)}), 500


def validate_node_key(node_key: str, node_type: str) -> bool:
    """Валидация ключа узла"""
    if node_type == 'concept' and not node_key.startswith('c:'):
        return False
    elif node_type == 'technology' and not node_key.startswith('t:'):
        return False
    elif node_type == 'version' and not node_key.startswith('v:'):
        return False
    elif node_type == 'directory' and not node_key.startswith('d:'):
        return False
    elif node_type == 'module' and not node_key.startswith('m:'):
        return False
    elif node_type == 'other':
        # Для типа 'other' ключ может быть любым
        return True
    return True


def get_expected_prefix(node_type: str) -> str:
    """Получить ожидаемый префикс для типа узла"""
    prefixes = {
        'concept': 'c:',
        'technology': 't:',
        'version': 'v:',
        'directory': 'd:',
        'module': 'm:',
        'other': 'любой'
    }
    return prefixes.get(node_type, 'неизвестный')


def check_node_key_exists(node_key: str) -> bool:
    """Проверить существование узла с указанным ключом"""
    try:
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            query = f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (n {{arango_key: '{node_key}'}})
                    RETURN count(n) as count
                $$) AS (count agtype);
            """
            cur.execute(query)
            result = cur.fetchone()
            count = agtype_to_python(result[0]) if result else 0
            return count > 0
    except Exception as e:
        log(f"Error checking node key existence: {e}")
        return False


def create_node_in_db(node_key: str, node_name: str, node_type: str, properties: dict) -> int:
    """Создать узел в базе данных"""
    try:
        # Подготовить дополнительные свойства
        extra_props = ""
        if properties:
            props_list = []
            for key, value in properties.items():
                if isinstance(value, str):
                    props_list.append(f"{key}: '{value}'")
                else:
                    props_list.append(f"{key}: {value}")
            extra_props = ", " + ", ".join(props_list)
        
        # Cypher запрос для создания узла
        query = f"""
            SELECT * FROM cypher('{graph_name}', $$
                CREATE (n:canonical_node {{
                    arango_key: '{node_key}',
                    name: '{node_name}',
                    node_type: '{node_type}'{extra_props}
                }})
                RETURN id(n)
            $$) AS (node_id agtype);
        """
        
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute(query)
            result = cur.fetchone()
            
            if result and result[0]:
                return agtype_to_python(result[0])
            else:
                raise Exception("Не удалось получить ID созданного узла")
                
    except Exception as e:
        log(f"Error creating node in DB: {e}")
        raise


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Построить граф используя PostgreSQL функции"""
    try:
        start = request.args.get('start', '')
        depth = int(request.args.get('depth', '5'))
        project = request.args.get('project', '') or None
        theme = request.args.get('theme', 'dark')
        
        # Используем новые PostgreSQL функции вместо прямых Cypher запросов
        if not start:
            # Вернуть все узлы и ребра проекта
            # Получаем рёбра
            edge_results = execute_sql_function('ag_catalog.get_all_graph_for_viewer', project)
            # Получаем все узлы (включая изолированные)
            all_node_results = execute_sql_function('ag_catalog.get_all_nodes_for_viewer', project if project else None)
            
            # Определяем изолированные узлы
            connected_node_ids = set()
            for row in edge_results:
                if len(row) == 11:  # Это ребро
                    from_id = agtype_to_python(row[1])
                    to_id = agtype_to_python(row[2])
                    connected_node_ids.add(str(from_id))
                    connected_node_ids.add(str(to_id))
            
            log(f"Connected node IDs: {len(connected_node_ids)}")
            log(f"All nodes count: {len(all_node_results)}")
            
            # Фильтруем изолированные узлы
            isolated_nodes = []
            for row in all_node_results:
                if len(row) == 3:  # Это узел
                    node_id = str(agtype_to_python(row[0]))
                    node_key = agtype_to_python(row[1])
                    if node_id not in connected_node_ids:
                        isolated_nodes.append(row)
                        log(f"Isolated node found: {node_key} (ID: {node_id})")
            
            log(f"Isolated nodes count: {len(isolated_nodes)}")
            
            # Объединяем результаты
            results = list(edge_results) + isolated_nodes
        else:
            # Извлечь ключ узла из start
            start_key = start.split('/')[-1] if '/' in start else start
            # Используем функцию get_graph_for_viewer, которая работает с edge_projects
            # Функция возвращает 11 колонок: edge_id, from_id, to_id, from_name, to_name, 
            # from_key, to_key, from_kind, to_kind, projects, rel_type
            results = execute_sql_function(
                'ag_catalog.get_graph_for_viewer',
                start_key,
                depth,
                project if project else None
            )
        
        # Построение узлов и рёбер для vis-network
        nodes_map = {}
        edges_map = {}
        
        # Локальный кэш канонических направлений рёбер
        canonical_edge_dir = {}

        # Кэш свойств узлов по id
        node_props_cache = {}

        def get_node_props(node_id: int):
            if node_id in node_props_cache:
                return node_props_cache[node_id]
            try:
                with db_conn.cursor() as cur:
                    cur.execute("LOAD 'age';")
                    cur.execute("SET search_path = ag_catalog, public;")
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (n) WHERE id(n) = {int(node_id)}
                            RETURN n.arango_key, n.name
                        $$) as (key agtype, name agtype);
                    """)
                    row = cur.fetchone()
                    key = agtype_to_python(row[0]) if row else None
                    name = agtype_to_python(row[1]) if row else None
                    # Запасной вариант: если имя пусто, используем ключ
                    if not name:
                        name = key or str(node_id)
                    node_props_cache[node_id] = (key or str(node_id), name)
                    return node_props_cache[node_id]
            except Exception:
                node_props_cache[node_id] = (str(node_id), str(node_id))
                return node_props_cache[node_id]

        def get_canonical_from_to(eid: int):
            if eid in canonical_edge_dir:
                return canonical_edge_dir[eid]
            try:
                with db_conn.cursor() as cur:
                    cur.execute("LOAD 'age';")
                    cur.execute("SET search_path = ag_catalog, public;")
                    # Явно указываем две колонки, чтобы не зависеть от эвристик execute_cypher
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (a)-[e]->(b) WHERE id(e) = {eid}
                            RETURN id(a), id(b)
                        $$) as (a_id agtype, b_id agtype);
                    """)
                    row = cur.fetchone()
                    if row and row[0] is not None and row[1] is not None:
                        a_id = agtype_to_python(row[0])
                        b_id = agtype_to_python(row[1])
                        canonical_edge_dir[eid] = (a_id, b_id)
                        return a_id, b_id
                    # Резервный способ: вернуть само ребро и прочитать start_id/end_id
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH ()-[e]->() WHERE id(e) = {eid}
                            RETURN e
                        $$) as (edge agtype);
                    """)
                    row2 = cur.fetchone()
                    if row2 and row2[0] is not None:
                        e_obj = agtype_to_python(row2[0])
                        if isinstance(e_obj, dict):
                            s_id = e_obj.get('start_id')
                            t_id = e_obj.get('end_id')
                            if s_id is not None and t_id is not None:
                                canonical_edge_dir[eid] = (int(s_id), int(t_id))
                                return int(s_id), int(t_id)
            except Exception:
                pass
            return None, None

        for row in results:
            # Определяем тип строки по количеству колонок
            if len(row) == 11:
                # Это ребро
                edge_id = agtype_to_python(row[0])
                from_id = agtype_to_python(row[1])
                to_id = agtype_to_python(row[2])
                from_name = agtype_to_python(row[3])
                to_name = agtype_to_python(row[4])
                from_key = agtype_to_python(row[5])
                to_key = agtype_to_python(row[6])
                from_kind = agtype_to_python(row[7])
                to_kind = agtype_to_python(row[8])
                projects = agtype_to_python(row[9])
                rel_type = agtype_to_python(row[10])

                # Нормализация направления: берём каноническое направление из базы
                can_from, can_to = get_canonical_from_to(edge_id)
                if can_from is not None and can_to is not None:
                    from_id, to_id = can_from, can_to
                
                # Переопределяем свойства узлов по их фактическим id, чтобы исключить несоответствие колонок
                f_key, f_name = get_node_props(from_id)
                t_key, t_name = get_node_props(to_id)
                from_key, to_key = f_key, t_key
                from_name, to_name = f_name, t_name
                
                # Обрабатываем ребро
                process_edge(edge_id, from_id, to_id, from_name, to_name, from_key, to_key, 
                           from_kind, to_kind, projects, rel_type, project, theme, nodes_map, edges_map)
            elif len(row) == 3:
                # Это узел из get_all_nodes_for_viewer
                node_id = agtype_to_python(row[0])
                node_key = agtype_to_python(row[1])
                node_name = agtype_to_python(row[2])
                
                # Обрабатываем узел (изолированный)
                process_isolated_node(node_id, node_key, node_name, theme, nodes_map)
            else:
                # Неизвестный формат
                log(f"Unknown row format with {len(row)} columns: {row}")
                continue
        
        # Пост-нормализация направления рёбер на основе каноники
        normalized_edges = []
        for e in edges_map.values():
            eid = e.get('id')
            if eid is not None:
                can_from, can_to = get_canonical_from_to(eid)
                if can_from is not None and can_to is not None:
                    e['from'] = can_from
                    e['to'] = can_to
            normalized_edges.append(e)

        # Отдаём сегмент из БД без дополнительной фильтрации: минимальный путь БД→API→Фронт
        result = {
            'theme': theme,
            'nodes': list(nodes_map.values()),
            'edges': normalized_edges
        }
        
        return jsonify(result)
    except Exception as e:
        log(f"Error in get_graph: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/object_details', methods=['GET'])
def get_object_details():
    """Получить детали объекта.
    Поддерживает:
      - Графовые объекты AGE по id/ключу (по умолчанию)
      - Документные коллекции из PostgreSQL: collection=projects|rules & key=...
    """
    try:
        collection = request.args.get('collection')
        key = request.args.get('key')
        if collection and key:
            with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                if collection == 'projects':
                    cur.execute("SELECT key, name, description, data, created_at, updated_at FROM public.projects WHERE key=%s", (key,))
                elif collection == 'rules':
                    cur.execute("SELECT key, title, description, data, created_at, updated_at FROM public.rules WHERE key=%s", (key,))
                else:
                    return jsonify({'error': f'Unsupported collection: {collection}'}), 400
                row = cur.fetchone()
                if not row:
                    return jsonify({'error': f'{collection}/{key} not found'}), 404
                return jsonify(row)
        
        # Графовый режим (обратная совместимость)
        doc_id = request.args.get('id', '')
        if not doc_id:
            return jsonify({'error': 'Missing "id" or (collection,key)'}), 400
        
        try:
            obj_id = int(doc_id)
            query = "MATCH (n) WHERE id(n) = $obj_id RETURN n"
            params = {'obj_id': obj_id}
            results = execute_cypher(query, params)
            if not results or not results[0][0]:
                query = "MATCH ()-[r]->() WHERE id(r) = $obj_id RETURN r"
                results = execute_cypher(query, params, return_type='edge')
        except ValueError:
            k = doc_id.split('/')[-1] if '/' in doc_id else doc_id
            query = "MATCH (n {arango_key: $key}) RETURN n"
            params = {'key': k}
            results = execute_cypher(query, params)
            if not results or not results[0][0]:
                query = "MATCH ()-[r {arango_key: $key}]->() RETURN r"
                results = execute_cypher(query, params, return_type='edge')
        
        if not results or not results[0][0]:
            return jsonify({'error': f'Object "{doc_id}" not found'}), 404
        obj_data = agtype_to_python(results[0][0])
        
        # Обогатить данные проектов структурированной информацией
        # Для рёбер передаём edge_id для использования нормализованной структуры
        if 'start_id' in obj_data and 'end_id' in obj_data:
            # Это ребро, используем нормализованную структуру
            enriched_data = enrich_object_properties(db_conn, obj_data, edge_id=obj_data.get('id'))
        else:
            # Это узел, используем обычное обогащение
            enriched_data = enrich_object_properties(db_conn, obj_data)
        
        return jsonify(enriched_data)
    except Exception as e:
        log(f"Error in get_object_details: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/canonical_edge', methods=['GET'])
def canonical_edge():
    """Диагностика: вернуть каноническое направление рёбра по edge_id."""
    try:
        eid = request.args.get('id')
        if not eid:
            return jsonify({'error': 'Missing id'}), 400
        try:
            edge_id = int(eid)
        except ValueError:
            return jsonify({'error': 'Invalid id'}), 400

        # Локальная функция может находиться ниже по файлу; дублируем минимальную логику
        def _get_canonical(edge_id: int):
            try:
                with db_conn.cursor() as cur:
                    cur.execute("LOAD 'age';")
                    cur.execute("SET search_path = ag_catalog, public;")
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (a)-[e]->(b) WHERE id(e) = {edge_id}
                            RETURN id(a), id(b)
                        $$) as (a_id agtype, b_id agtype);
                    """)
                    row = cur.fetchone()
                    if row and row[0] is not None and row[1] is not None:
                        a_id = agtype_to_python(row[0])
                        b_id = agtype_to_python(row[1])
                        return int(a_id), int(b_id)
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH ()-[e]->() WHERE id(e) = {edge_id}
                            RETURN e
                        $$) as (edge agtype);
                    """)
                    row2 = cur.fetchone()
                    if row2 and row2[0] is not None:
                        e_obj = agtype_to_python(row2[0])
                        if isinstance(e_obj, dict):
                            s_id = e_obj.get('start_id')
                            t_id = e_obj.get('end_id')
                            if s_id is not None and t_id is not None:
                                return int(s_id), int(t_id)
            except Exception as ex:
                log(f"canonical_edge error: {ex}")
            return None, None

        a, b = _get_canonical(edge_id)
        return jsonify({ 'id': edge_id, 'from': a, 'to': b })
    except Exception as e:
        log(f"Error in canonical_edge: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/expand_node', methods=['GET'])
def expand_node():
    """Получить соседние узлы используя PostgreSQL функцию"""
    try:
        node_id = request.args.get('node_id', '')
        direction = request.args.get('direction', 'outbound')  # Пока не используется, функция возвращает both
        project = request.args.get('project', '')
        theme = request.args.get('theme', 'dark')
        depth = int(request.args.get('depth', '1'))  # По умолчанию 1 уровень
        
        if not node_id:
            return jsonify({'error': 'Missing "node_id" parameter'}), 400
        
        # Получить arango_key по node_id
        node_key = None
        if node_id.isdigit():
            # Это числовой ID, нужно получить arango_key из базы
            with db_conn.cursor() as cur:
                cur.execute("LOAD 'age';")
                cur.execute("SET search_path = ag_catalog, public;")
                cur.execute(f"""
                    SELECT * FROM cypher('{graph_name}', $$
                        MATCH (n) WHERE id(n) = {node_id}
                        RETURN n.arango_key
                    $$) as (key agtype);
                """)
                result = cur.fetchone()
                if result:
                    node_key = agtype_to_python(result[0])
        else:
            # Это уже ключ (например, 'canonical_nodes/c:project')
            node_key = node_id.split('/')[-1] if '/' in node_id else node_id
        
        if not node_key:
            return jsonify({'error': f'Node not found: {node_id}'}), 404
        
        # Используем новую PostgreSQL функцию
        results = execute_sql_function(
            'ag_catalog.expand_node_for_viewer',
            node_key,
            depth,
            project if project else None
        )
        
        # Форматирование для vis-network
        nodes = []
        edges = []
        processed_nodes = set()
        processed_edges = set()
        
        for row in results:
            node_id_val = agtype_to_python(row[0])
            node_key_val = agtype_to_python(row[1])
            node_name = agtype_to_python(row[2])
            node_kind = agtype_to_python(row[3])
            edge_id = agtype_to_python(row[4])
            from_id = agtype_to_python(row[5])
            to_id = agtype_to_python(row[6])
            edge_projects_str = agtype_to_python(row[7])
            direction = agtype_to_python(row[8])
            
            # Парсинг projects - agtype_to_python уже преобразует в Python объект
            if edge_projects_str and isinstance(edge_projects_str, list):
                edge_projects = edge_projects_str
            elif edge_projects_str and isinstance(edge_projects_str, str):
                try:
                    edge_projects = json.loads(edge_projects_str)
                except:
                    edge_projects = []
            else:
                edge_projects = []
            
            # Добавить узел (избегать дубликатов)
            if node_id_val and node_id_val not in processed_nodes:
                processed_nodes.add(node_id_val)
                nodes.append({
                    'id': node_id_val,
                    'label': node_name or node_key_val,
                    'shape': 'box' if node_kind == 'concept' else 'ellipse',
                    'color': {
                        'background': '#263238' if theme == 'dark' else '#E3F2FD'
                    } if node_kind == 'concept' else {
                        'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
                    }
                })
            
            # Добавить ребро (избегать дубликатов)
            if edge_id and edge_id not in processed_edges:
                processed_edges.add(edge_id)
                edges.append({
                    'id': edge_id,
                    'from': from_id,
                    'to': to_id,
                    'label': ', '.join(edge_projects) if edge_projects else 'альтернатива',
                    'color': {
                        'color': '#64B5F6' if edge_projects else '#9E9E9E'
                    }
                })
        
        log(f"expand_node: {node_key} (depth={depth}) -> {len(nodes)} nodes, {len(edges)} edges")
        
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        log(f"Error in expand_node: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/subgraph', methods=['GET'])
def get_subgraph():
    """Получить все узлы и рёбра в подграфе"""
    try:
        node_id = request.args.get('node_id', '')
        direction = request.args.get('direction', 'outbound')
        max_depth = int(request.args.get('max_depth', '100'))
        
        if not node_id:
            return jsonify({'error': 'Missing "node_id" parameter'}), 400
        
        # Преобразовать node_id
        try:
            nid = int(node_id)
        except:
            key = node_id.split('/')[-1] if '/' in node_id else node_id
            results = execute_cypher("MATCH (n {arango_key: $key}) RETURN id(n)", {'key': key})
            if not results:
                return jsonify({'error': f'Node {node_id} not found'}), 404
            nid = agtype_to_python(results[0][0])
        
        # Упрощенное решение - ищем связанные узлы в уже загруженных данных
        # Apache AGE имеет серьезные ограничения с синтаксисом Cypher
        
        # Получаем все рёбра из базы
        try:
            if direction == 'outbound':
                # Ищем исходящие рёбра
                query = "MATCH (start)-[e:project_relation]->(end) WHERE id(start) = $node_id RETURN id(end), id(e)"
            else:  # inbound
                # Ищем входящие рёбра
                query = "MATCH (start)<-[e:project_relation]-(end) WHERE id(start) = $node_id RETURN id(end), id(e)"
            
            results = execute_cypher(query, {'node_id': nid})
        except Exception as e:
            # Если Cypher не работает, возвращаем пустой результат
            log(f"Cypher query failed: {e}")
            results = []
        
        # Извлечение уникальных ID
        node_ids = set()
        edge_ids = set()
        
        for row in results:
            if row[0]:
                node_ids.add(agtype_to_python(row[0]))
            if row[1]:
                edge_ids.add(agtype_to_python(row[1]))
        
        return jsonify({
            'node_ids': list(node_ids),
            'edge_ids': list(edge_ids)
        })
    except Exception as e:
        log(f"Error in get_subgraph: {e}")
        return jsonify({'error': str(e)}), 500


# ========== EDGE MANAGEMENT ENDPOINTS ==========

@app.route('/api/edges', methods=['POST'])
def create_edge():
    """Создать новое ребро с валидацией уникальности"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        # Преобразовать _from и _to в AGE ID
        from_id = data.get('_from')
        to_id = data.get('_to')
        
        if not from_id or not to_id:
            return jsonify({'success': False, 'error': 'Отсутствуют _from или _to'}), 400
        
        # Преобразовать arango-style IDs/ключи в AGE IDs
        try:
            from_vertex_id = convert_node_key_to_age_id(from_id)
            to_vertex_id = convert_node_key_to_age_id(to_id)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Подготовить свойства
        properties = {k: v for k, v in data.items() if not k.startswith('_')}
        
        # Вставка с валидацией
        result = edge_validator.insert_edge_safely(from_vertex_id, to_vertex_id, properties)
        
        log(f"✓ Edge created: {result.get('edge_id')} ({from_vertex_id} → {to_vertex_id})")
        
        return jsonify({'success': True, 'edge': result})
        
    except ValueError as e:
        log(f"✗ Edge validation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 409
    except Exception as e:
        log(f"✗ Error creating edge: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/<int:edge_id>', methods=['PUT'])
def update_edge(edge_id):
    """Обновить существующее ребро"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        # Подготовить новые свойства (только не-системные поля)
        new_properties = {k: v for k, v in data.items() if not k.startswith('_')}
        
        # Обновление с валидацией
        result = edge_validator.update_edge_safely(edge_id, new_properties)
        
        log(f"✓ Edge updated: {edge_id}")
        
        return jsonify({'success': True, 'edge': result})
        
    except ValueError as e:
        log(f"✗ Edge validation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 409
    except RuntimeError as e:
        log(f"✗ Edge not found: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        log(f"✗ Error updating edge: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/<int:edge_id>', methods=['DELETE'])
def delete_edge(edge_id):
    """Удалить ребро"""
    try:
        edge_validator.delete_edge(edge_id)
        
        log(f"✓ Edge deleted: {edge_id}")
        
        return jsonify({
            'success': True,
            'message': f'Ребро {edge_id} успешно удалено'
        })
        
    except RuntimeError as e:
        log(f"✗ Edge not found: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        log(f"✗ Error deleting edge: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/check', methods=['POST'])
def check_edge_uniqueness():
    """Проверить уникальность связи между узлами"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        from_id = data.get('_from')
        to_id = data.get('_to')
        exclude_edge_id = data.get('exclude_edge_id')
        
        if not from_id or not to_id:
            return jsonify({
                'success': False,
                'error': 'Отсутствуют обязательные поля _from и _to'
            }), 400
        
        # Преобразовать arango IDs/ключи в AGE IDs
        try:
            from_vertex_id = convert_node_key_to_age_id(from_id)
            to_vertex_id = convert_node_key_to_age_id(to_id)
            exclude_id = convert_edge_key_to_age_id(exclude_edge_id) if exclude_edge_id else None
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        is_unique, error_msg = edge_validator.check_edge_uniqueness(
            from_vertex_id,
            to_vertex_id,
            exclude_id
        )
        
        return jsonify({
            'is_unique': is_unique,
            'error': error_msg
        })
        
    except Exception as e:
        log(f"✗ Error checking edge uniqueness: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== EDGE PROJECTS MANAGEMENT ENDPOINTS ==========

@app.route('/api/edges/<int:edge_id>/projects', methods=['GET'])
def get_edge_projects(edge_id):
    """Получить список проектов, связанных с ребром"""
    try:
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Получить проекты через PostgreSQL функцию
            cur.execute("""
                SELECT project_info, role, weight, created_at, created_by, metadata
                FROM ag_catalog.get_edge_projects_enriched(%s)
            """, (edge_id,))
            
            projects_data = cur.fetchall()
            
            # Форматировать результаты
            projects = []
            for row in projects_data:
                project_info = row[0]  # JSONB с информацией о проекте
                projects.append({
                    'key': project_info.get('id'),
                    'name': project_info.get('name'),
                    'description': project_info.get('description'),
                    'role': row[1],  # роль в связи
                    'weight': float(row[2]) if row[2] else 1.0,  # вес связи
                    'created_at': row[3].isoformat() if row[3] else None,
                    'created_by': row[4],
                    'metadata': row[5] if row[5] else {}
                })
            
            return jsonify({
                'success': True,
                'edge_id': edge_id,
                'projects': projects
            })
            
    except Exception as e:
        log(f"✗ Error getting projects for edge {edge_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/<int:edge_id>/projects', methods=['POST'])
def add_project_to_edge(edge_id):
    """Добавить проект к ребру"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        project_key = data.get('project_key')
        if not project_key:
            return jsonify({'success': False, 'error': 'Отсутствует обязательное поле project_key'}), 400
        
        role = data.get('role', 'participant')
        weight = float(data.get('weight', 1.0))
        created_by = data.get('created_by', 'api')
        metadata = data.get('metadata', {})
        
        # Проверить существование ребра
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Проверка существования ребра
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH ()-[e]->() WHERE id(e) = {edge_id}
                    RETURN id(e)
                $$) AS (edge_id agtype);
            """)
            if not cur.fetchone():
                return jsonify({'success': False, 'error': f'Ребро с ID {edge_id} не найдено'}), 404
            
            # Добавить проект к ребру
            try:
                cur.execute("""
                    SELECT ag_catalog.add_project_to_edge(
                        %s, %s, %s, %s, %s, %s::jsonb
                    )
                """, (edge_id, project_key, role, weight, created_by, json.dumps(metadata)))
                
                result = cur.fetchone()
                if result and result[0]:
                    log(f"✓ Project {project_key} added to edge {edge_id}")
                    return jsonify({
                        'success': True,
                        'message': f'Проект {project_key} добавлен к ребру {edge_id}',
                        'edge_id': edge_id,
                        'project_key': project_key
                    })
                else:
                    return jsonify({'success': False, 'error': 'Не удалось добавить проект'}), 500
                    
            except Exception as e:
                error_msg = str(e)
                if 'not found' in error_msg.lower():
                    return jsonify({'success': False, 'error': f'Проект {project_key} не найден'}), 404
                else:
                    raise
        
    except Exception as e:
        log(f"✗ Error adding project to edge {edge_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/<int:edge_id>/projects/<project_key>', methods=['DELETE'])
def remove_project_from_edge(edge_id, project_key):
    """Удалить проект из ребра"""
    try:
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Проверка существования ребра
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH ()-[e]->() WHERE id(e) = {edge_id}
                    RETURN id(e)
                $$) AS (edge_id agtype);
            """)
            if not cur.fetchone():
                return jsonify({'success': False, 'error': f'Ребро с ID {edge_id} не найдено'}), 404
            
            # Удалить проект из ребра
            try:
                cur.execute("""
                    SELECT ag_catalog.remove_project_from_edge(%s, %s)
                """, (edge_id, project_key))
                
                result = cur.fetchone()
                if result and result[0]:
                    log(f"✓ Project {project_key} removed from edge {edge_id}")
                    return jsonify({
                        'success': True,
                        'message': f'Проект {project_key} удалён из ребра {edge_id}',
                        'edge_id': edge_id,
                        'project_key': project_key
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Проект {project_key} не связан с ребром {edge_id}'
                    }), 404
                    
            except Exception as e:
                error_msg = str(e)
                if 'not found' in error_msg.lower():
                    return jsonify({'success': False, 'error': f'Проект {project_key} не найден'}), 404
                else:
                    raise
        
    except Exception as e:
        log(f"✗ Error removing project from edge {edge_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/<int:edge_id>', methods=['GET'])
def get_edge_info(edge_id):
    """Получить полную информацию о ребре (узлы, тип связи, проекты)"""
    try:
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Получить информацию о ребре из графа
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (a)-[e]->(b) WHERE id(e) = {edge_id}
                    RETURN id(a), a.arango_key, a.name, a.kind,
                           id(b), b.arango_key, b.name, b.kind,
                           e.relationType
                $$) AS (from_id agtype, from_key agtype, from_name agtype, from_kind agtype,
                        to_id agtype, to_key agtype, to_name agtype, to_kind agtype,
                        rel_type agtype);
            """)
            
            edge_row = cur.fetchone()
            if not edge_row:
                return jsonify({'success': False, 'error': f'Ребро с ID {edge_id} не найдено'}), 404
            
            # Конвертировать значения
            from_id = agtype_to_python(edge_row[0])
            from_key = agtype_to_python(edge_row[1])
            from_name = agtype_to_python(edge_row[2])
            from_kind = agtype_to_python(edge_row[3])
            to_id = agtype_to_python(edge_row[4])
            to_key = agtype_to_python(edge_row[5])
            to_name = agtype_to_python(edge_row[6])
            to_kind = agtype_to_python(edge_row[7])
            rel_type = agtype_to_python(edge_row[8])
            
            # Получить проекты
            cur.execute("""
                SELECT project_info
                FROM ag_catalog.get_edge_projects_enriched(%s)
            """, (edge_id,))
            
            projects_data = cur.fetchall()
            projects = []
            for row in projects_data:
                project_info = row[0]  # JSONB
                projects.append(project_info.get('id'))  # key проекта
            
            return jsonify({
                'success': True,
                'edge': {
                    'edge_id': edge_id,
                    'from': {
                        'id': from_id,
                        'key': from_key,
                        'name': from_name,
                        'kind': from_kind
                    },
                    'to': {
                        'id': to_id,
                        'key': to_key,
                        'name': to_name,
                        'kind': to_kind
                    },
                    'relation_type': rel_type,
                    'projects': projects
                }
            })
            
    except Exception as e:
        log(f"✗ Error getting edge info for {edge_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/check-connection', methods=['POST'])
def check_connection():
    """Проверить связь/пути между узлами с таймаутами и режимами.
    Режимы:
      - direct: только прямое ребро A→B
      - reachable: существует ли путь A⇢B (кратчайший)
      - paths: вернуть некоторые пути A⇢B (усечённо, в пределах времени)
    Ограничение выполнения задаётся временем (statement_timeout + watchdog).
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

        from_node = data.get('from_node')
        to_node = data.get('to_node')
        project_filter = data.get('project_filter')
        mode = (data.get('mode') or 'direct').lower()
        direction = (data.get('direction') or 'outbound').lower()
        time_limit_ms = int(data.get('time_limit_ms') or 2000)
        hard_kill_ms = int(data.get('hard_kill_ms') or (time_limit_ms + 500))
        enumerate_nodes_only = bool(data.get('enumerate_nodes_only', True))
        return_partial = bool(data.get('return_partial', True))

        if not from_node or not to_node:
            return jsonify({'success': False, 'error': 'Отсутствуют обязательные поля from_node и to_node'}), 400

        # Преобразовать в AGE IDs
        try:
            from_vertex_id = convert_node_key_to_age_id(from_node)
            to_vertex_id = convert_node_key_to_age_id(to_node)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        start_ts = time.monotonic()
        elapsed_ms = lambda: int((time.monotonic() - start_ts) * 1000)

        result_payload = {
            'connected': False,
            'elapsed_ms': 0,
            'timed_out': False,
        }

        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")

            # Сначала быстрая проверка прямой связи (независимо от mode)
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (a)-[e]->(b)
                    WHERE id(a) = {from_vertex_id} AND id(b) = {to_vertex_id}
                    RETURN id(e), e.relationType
                    LIMIT 1
                $$) AS (edge_id agtype, rel_type agtype);
            """)
            direct_row = cur.fetchone()
            if direct_row:
                result_payload['connected'] = True
                result_payload['edge'] = {
                    'edge_id': agtype_to_python(direct_row[0]),
                    'from_node': from_vertex_id,
                    'to_node': to_vertex_id,
                    'relation_type': agtype_to_python(direct_row[1])
                }
                # Проекты прямой связи
                try:
                    cur.execute("""
                        SELECT project_info
                        FROM ag_catalog.get_edge_projects_enriched(%s)
                    """, (result_payload['edge']['edge_id'],))
                    edge_projects = [ (row[0] or {}).get('id') for row in cur.fetchall() ]
                    result_payload['edge']['projects'] = edge_projects
                except Exception:
                    result_payload['edge']['projects'] = []

            # Если только direct — возвращаем
            if mode == 'direct':
                result_payload['elapsed_ms'] = elapsed_ms()
                return jsonify(result_payload)

            # Дальше — режимы reachable/paths с таймаутом на стороне БД
            try:
                cur.execute(f"SET LOCAL statement_timeout = {int(hard_kill_ms)};")

                if direction == 'inbound':
                    rel_pattern = "<-[*1..100]-"
                else:
                    rel_pattern = "-[*1..100]->"

                if mode == 'reachable':
                    # Ищем кратчайший путь в пределах таймаута
                    query = f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (a), (b)
                            WHERE id(a) = {from_vertex_id} AND id(b) = {to_vertex_id}
                            MATCH p = (a){rel_pattern}(b)
                            RETURN count(p) as cnt, min(length(p)) as dist
                        $$) AS (cnt agtype, dist agtype);
                    """
                    cur.execute(query)
                    row = cur.fetchone()
                    cnt = agtype_to_python(row[0]) if row else 0
                    dist = agtype_to_python(row[1]) if row else None
                    result_payload['path_exists'] = bool(cnt and cnt > 0)
                    result_payload['shortest_distance'] = int(dist) if dist is not None else None
                elif mode == 'paths':
                    # Возвращаем некоторые пути как последовательности ключей узлов
                    # Список ключей: [n IN nodes(p) | n.arango_key]
                    query = f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (a), (b)
                            WHERE id(a) = {from_vertex_id} AND id(b) = {to_vertex_id}
                            MATCH p = (a){rel_pattern}(b)
                            RETURN [n IN nodes(p) | n.arango_key] as path_keys
                            LIMIT 100000
                        $$) AS (path_keys agtype);
                    """
                    cur.execute(query)
                    rows = cur.fetchall()
                    paths = [agtype_to_python(r[0]) for r in rows]
                    # Если только ключи, возвращаем сразу; иначе можно обогатить позже
                    result_payload['paths'] = paths
                    result_payload['truncated'] = False  # время контролирует сечение
                else:
                    # Неизвестный режим — трактуем как reachable
                    query = f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH (a), (b)
                            WHERE id(a) = {from_vertex_id} AND id(b) = {to_vertex_id}
                            MATCH p = (a){rel_pattern}(b)
                            RETURN count(p) as cnt, min(length(p)) as dist
                        $$) AS (cnt agtype, dist agtype);
                    """
                    cur.execute(query)
                    row = cur.fetchone()
                    cnt = agtype_to_python(row[0]) if row else 0
                    dist = agtype_to_python(row[1]) if row else None
                    result_payload['path_exists'] = bool(cnt and cnt > 0)
                    result_payload['shortest_distance'] = int(dist) if dist is not None else None

            except Exception as qe:
                # Таймаут или иная ошибка выполнения
                msg = str(qe)
                result_payload['timed_out'] = ('statement timeout' in msg.lower() or 'canceling statement' in msg.lower())
                if mode == 'reachable':
                    result_payload['path_exists'] = 'unknown'
                    result_payload['shortest_distance'] = None
                elif mode == 'paths':
                    if return_partial:
                        # Частичный возврат невозможен без курсора, поэтому просто помечаем усечение
                        result_payload['paths'] = []
                        result_payload['truncated'] = True
                    result_payload['advisory_risk'] = 'cycle_check_incomplete'
                else:
                    # Для direct мы сюда не попадаем
                    pass

            result_payload['elapsed_ms'] = elapsed_ms()
            return jsonify(result_payload)

    except Exception as e:
        log(f"✗ Error checking connection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/batch-add-projects', methods=['POST'])
def batch_add_projects():
    """Массовое добавление проекта к нескольким рёбрам"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        edge_ids = data.get('edge_ids')
        project_key = data.get('project_key')
        
        if not edge_ids or not isinstance(edge_ids, list):
            return jsonify({'success': False, 'error': 'Отсутствует обязательное поле edge_ids (массив)'}), 400
        
        if not project_key:
            return jsonify({'success': False, 'error': 'Отсутствует обязательное поле project_key'}), 400
        
        role = data.get('role', 'participant')
        weight = float(data.get('weight', 1.0))
        created_by = data.get('created_by', 'api')
        metadata = data.get('metadata', {})
        
        # Валидация edge_ids
        if len(edge_ids) == 0:
            return jsonify({'success': False, 'error': 'Массив edge_ids пуст'}), 400
        
        # Результаты операции
        results = []
        added_count = 0
        skipped_count = 0
        errors = []
        
        # Выполняем операции в одной транзакции
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            for edge_id in edge_ids:
                try:
                    # Проверка существования ребра
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH ()-[e]->() WHERE id(e) = {edge_id}
                            RETURN id(e)
                        $$) AS (edge_id agtype);
                    """)
                    if not cur.fetchone():
                        errors.append({
                            'edge_id': edge_id,
                            'error': 'Ребро не найдено'
                        })
                        continue
                    
                    # Добавить проект к ребру
                    try:
                        cur.execute("""
                            SELECT ag_catalog.add_project_to_edge(
                                %s, %s, %s, %s, %s, %s::jsonb
                            )
                        """, (edge_id, project_key, role, weight, created_by, json.dumps(metadata)))
                        
                        result = cur.fetchone()
                        if result and result[0]:
                            results.append({
                                'edge_id': edge_id,
                                'status': 'added'
                            })
                            added_count += 1
                            log(f"✓ Project {project_key} added to edge {edge_id}")
                        else:
                            results.append({
                                'edge_id': edge_id,
                                'status': 'skipped',
                                'reason': 'Не удалось добавить'
                            })
                            skipped_count += 1
                    except Exception as e:
                        error_msg = str(e)
                        if 'not found' in error_msg.lower() and 'project' in error_msg.lower():
                            errors.append({
                                'edge_id': edge_id,
                                'error': f'Проект {project_key} не найден'
                            })
                        else:
                            errors.append({
                                'edge_id': edge_id,
                                'error': error_msg
                            })
                        
                except Exception as e:
                    errors.append({
                        'edge_id': edge_id,
                        'error': str(e)
                    })
        
        return jsonify({
            'success': True,
            'project_key': project_key,
            'total': len(edge_ids),
            'added': added_count,
            'skipped': skipped_count,
            'errors': errors,
            'results': results
        })
        
    except Exception as e:
        log(f"✗ Error in batch_add_projects: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/edges/batch-remove-projects', methods=['POST'])
def batch_remove_projects():
    """Массовое удаление проекта из нескольких рёбер"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400
        
        edge_ids = data.get('edge_ids')
        project_key = data.get('project_key')
        
        if not edge_ids or not isinstance(edge_ids, list):
            return jsonify({'success': False, 'error': 'Отсутствует обязательное поле edge_ids (массив)'}), 400
        
        if not project_key:
            return jsonify({'success': False, 'error': 'Отсутствует обязательное поле project_key'}), 400
        
        # Валидация edge_ids
        if len(edge_ids) == 0:
            return jsonify({'success': False, 'error': 'Массив edge_ids пуст'}), 400
        
        # Результаты операции
        removed_count = 0
        not_found_count = 0
        errors = []
        
        # Выполняем операции
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            for edge_id in edge_ids:
                try:
                    # Проверка существования ребра
                    cur.execute(f"""
                        SELECT * FROM cypher('{graph_name}', $$
                            MATCH ()-[e]->() WHERE id(e) = {edge_id}
                            RETURN id(e)
                        $$) AS (edge_id agtype);
                    """)
                    if not cur.fetchone():
                        errors.append({
                            'edge_id': edge_id,
                            'error': 'Ребро не найдено'
                        })
                        continue
                    
                    # Удалить проект из ребра
                    try:
                        cur.execute("""
                            SELECT ag_catalog.remove_project_from_edge(%s, %s)
                        """, (edge_id, project_key))
                        
                        result = cur.fetchone()
                        if result and result[0]:
                            removed_count += 1
                            log(f"✓ Project {project_key} removed from edge {edge_id}")
                        else:
                            not_found_count += 1
                            log(f"⚠ Project {project_key} not found on edge {edge_id}")
                    except Exception as e:
                        error_msg = str(e)
                        if 'not found' in error_msg.lower() and 'project' in error_msg.lower():
                            errors.append({
                                'edge_id': edge_id,
                                'error': f'Проект {project_key} не найден'
                            })
                        else:
                            errors.append({
                                'edge_id': edge_id,
                                'error': error_msg
                            })
                        
                except Exception as e:
                    errors.append({
                        'edge_id': edge_id,
                        'error': str(e)
                    })
        
        return jsonify({
            'success': True,
            'project_key': project_key,
            'total': len(edge_ids),
            'removed': removed_count,
            'not_found': not_found_count,
            'errors': errors
        })
        
    except Exception as e:
        log(f"✗ Error in batch_remove_projects: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Удалить узел из графа (только если нет связанных рёбер)"""
    try:
        # 1. Проверить существование узла
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Получить информацию об узле
            node_query = f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (n) WHERE id(n) = {node_id}
                    RETURN n.arango_key, n.name
                $$) AS (key agtype, name agtype);
            """
            cur.execute(node_query)
            node_result = cur.fetchone()
            
            if not node_result:
                return jsonify({'error': f'Узел с ID {node_id} не найден'}), 404
            
            node_key = agtype_to_python(node_result[0])
            node_name = agtype_to_python(node_result[1])
        
        # 2. Проверить связанные рёбра
        edges_query = f"""
            SELECT * FROM cypher('{graph_name}', $$
                MATCH (n)-[r]-(m) WHERE id(n) = {node_id}
                RETURN count(r) as edge_count
            $$) AS (count agtype);
        """
        
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute(edges_query)
            edge_count = agtype_to_python(cur.fetchone()[0])
            
            if edge_count > 0:
                return jsonify({
                    'error': f'Узел {node_key} ({node_name}) имеет {edge_count} связанных рёбер',
                    'suggestion': 'Сначала удалите все рёбра, затем повторите удаление узла'
                }), 409
        
        # 3. Удалить узел (рёбер нет)
        delete_query = f"""
            SELECT * FROM cypher('{graph_name}', $$
                MATCH (n) WHERE id(n) = {node_id}
                DELETE n
                RETURN 'deleted'
            $$) AS (result agtype);
        """
        
        with db_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute(delete_query)
        
        log(f"✓ Node deleted: {node_id} ({node_key})")
        
        return jsonify({
            'success': True,
            'message': f'Узел {node_key} ({node_name}) успешно удален',
            'node_id': node_id
        })
        
    except Exception as e:
        log(f"✗ Error deleting node {node_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request_selection', methods=['GET'])
def request_selection_endpoint():
    """Endpoint для MCP команды: запросить выборку у браузера через WebSocket"""
    try:
        timeout = float(request.args.get('timeout', '3.0'))
        
        # Запросить выборку у браузера
        def request_selection_from_browser(timeout=3.0):
            global _selection_response
            
            with _selection_lock:
                _selection_response = None
            
            log("→ Requesting selection from browser...")
            socketio.emit('request_selection', {'timestamp': time.time()})
            
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                with _selection_lock:
                    if _selection_response is not None:
                        log("✓ Selection received from browser")
                        return _selection_response
                time.sleep(0.05)
            
            log("✗ Timeout waiting for selection from browser")
            return None
        
        selection = request_selection_from_browser(timeout=timeout)
        
        if selection is None:
            return jsonify({
                'status': 'timeout',
                'message': 'Браузер не ответил в течение заданного времени. Возможно, Graph Viewer не открыт.'
            }), 408
        
        return jsonify({'status': 'success', 'selection': selection})
        
    except Exception as e:
        log(f"Error in request_selection_endpoint: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ========== WEBSOCKET HANDLERS ==========

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    log(f"✓ WebSocket client connected: {request.sid}")
    emit('connection_established', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    log(f"✗ WebSocket client disconnected: {request.sid}")


@socketio.on('selection_response')
def handle_selection_response(data):
    """Обработка ответа от браузера с текущей выборкой"""
    global _selection_response
    
    with _selection_lock:
        _selection_response = data
        log(f"✓ Received selection from browser: {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")


# ========== MAIN ==========

def main():
    parser = argparse.ArgumentParser(description='Graph Viewer API Server with PostgreSQL + AGE')
    parser.add_argument('--host', default='127.0.0.1', help='Host')
    parser.add_argument('--port', type=int, default=8899, help='Port')
    parser.add_argument('--db-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--db-name', default='fedoc', help='Database name')
    parser.add_argument('--db-user', default='postgres', help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    args = parser.parse_args()
    
    # Подключение к PostgreSQL
    log(f"Connecting to PostgreSQL at {args.db_host}:{args.db_port}...")
    
    global db_conn, edge_validator
    db_conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password
    )
    # Включаем autocommit чтобы избежать блокировки транзакций
    db_conn.autocommit = True
    log("✓ Connected to PostgreSQL (autocommit mode)")
    
    # Инициализация валидатора рёбер
    edge_validator = create_edge_validator(db_conn)
    log("✓ Edge validator initialized")
    
    # Запуск сервера
    log(f"🌐 API Server (Flask + SocketIO) running on http://{args.host}:{args.port}")
    log("📡 WebSocket endpoint: ws://{args.host}:{args.port}/socket.io/")
    log("Press Ctrl+C to stop")
    
    try:
        socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        log("\n✓ Server stopped")
    finally:
        if db_conn:
            db_conn.close()
            log("✓ Database connection closed")


if __name__ == '__main__':
    main()

