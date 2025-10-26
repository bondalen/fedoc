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
        return json.loads(s)
    except:
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
            results = execute_sql_function('ag_catalog.get_all_graph_for_viewer', project)
        else:
            # Извлечь ключ узла из start
            start_key = start.split('/')[-1] if '/' in start else start
            # Получить граф от указанного узла
            results = execute_sql_function('ag_catalog.get_graph_for_viewer', start_key, depth, project)
        
        # Построение узлов и рёбер для vis-network
        nodes_map = {}
        edges_map = {}
        
        for row in results:
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
            
            # Фильтрация по проекту
            if project and (not projects or project not in projects):
                continue
            
            # Добавить узлы
            if from_id not in nodes_map:
                nodes_map[from_id] = {
                    'id': from_id,
                    'label': from_name,
                    '_key': from_key,
                    'shape': 'box' if from_kind == 'concept' else 'ellipse',
                    'color': {
                        'background': '#263238' if theme == 'dark' else '#E3F2FD'
                    } if from_kind == 'concept' else {
                        'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
                    }
                }
            
            if to_id not in nodes_map:
                nodes_map[to_id] = {
                    'id': to_id,
                    'label': to_name,
                    '_key': to_key,
                    'shape': 'box' if to_kind == 'concept' else 'ellipse',
                    'color': {
                        'background': '#263238' if theme == 'dark' else '#E3F2FD'
                    } if to_kind == 'concept' else {
                        'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
                    }
                }
            
            # Добавить ребро
            if edge_id not in edges_map:
                edges_map[edge_id] = {
                    'id': edge_id,
                    'from': from_id,
                    'to': to_id,
                    'label': ', '.join(projects) if projects else 'альтернатива',
                    'color': {
                        'color': '#64B5F6' if projects else '#9E9E9E'
                    }
                }
        
        result = {
            'theme': theme,
            'nodes': list(nodes_map.values()),
            'edges': list(edges_map.values())
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

