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

# Добавить путь к модулям для импорта
sys.path.insert(0, str(Path(__file__).parent))

# Импорт валидатора рёбер для AGE
from edge_validator_age import create_edge_validator

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

def execute_cypher(query: str, params: dict = None):
    """
    Выполнить Cypher запрос к Apache AGE
    
    Args:
        query: Cypher запрос (без оберток cypher())
        params: Параметры запроса
    
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
        
        # Определить количество возвращаемых колонок по запросу
        if "edge_id" in query and "from_id" in query:
            # Запрос для графа - много колонок
            full_query = f"SELECT * FROM cypher('{graph_name}', $${query}$$) as (edge_id agtype, from_id agtype, to_id agtype, from_name agtype, to_name agtype, from_key agtype, to_key agtype, from_kind agtype, to_kind agtype, projects agtype, rel_type agtype)"
        else:
            # Запрос для узлов - 3 колонки
            full_query = f"SELECT * FROM cypher('{graph_name}', $${query}$$) as (id agtype, key agtype, name agtype)"
        
        cur.execute(full_query)
        
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
    
    # Убрать кавычки если это строка
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    
    # Попробовать распарсить как JSON
    try:
        return json.loads(s)
    except:
        return s


# ========== REST API ENDPOINTS ==========

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Вернуть список узлов"""
    try:
        project = request.args.get('project', '')
        
        if project:
            # Получить узлы, связанные с проектом
            query = f"""
            MATCH (a)-[e:project_relation]->(b)
            WHERE '{project}' IN e.projects
            WITH DISTINCT a as node
            RETURN id(node) as id, node.arango_key as key, node.name as name
            UNION
            MATCH (a)-[e:project_relation]->(b)
            WHERE '{project}' IN e.projects
            WITH DISTINCT b as node
            RETURN id(node) as id, node.arango_key as key, node.name as name
            """
            results = execute_cypher(query)
        else:
            # Все узлы
            query = """
            MATCH (n:canonical_node)
            RETURN id(n) as id, n.arango_key as key, n.name as name
            """
            results = execute_cypher(query)
        
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
    """Построить граф"""
    try:
        start = request.args.get('start', '')
        depth = int(request.args.get('depth', '5'))
        project = request.args.get('project', '') or None
        theme = request.args.get('theme', 'dark')
        
        # Если start не указан, вернуть все узлы и ребра проекта
        if not start:
            if project:
                query = f"""
                MATCH (n)-[e:project_relation]->(m)
                WHERE '{project}' IN e.projects
                RETURN 
                    id(e) as edge_id,
                    id(n) as from_id,
                    id(m) as to_id,
                    n.name as from_name,
                    m.name as to_name,
                    n.arango_key as from_key,
                    m.arango_key as to_key,
                    n.kind as from_kind,
                    m.kind as to_kind,
                    e.projects as projects,
                    e.relationType as rel_type
                LIMIT 5000
                """
            else:
                query = """
                MATCH (n)-[e:project_relation]->(m)
                RETURN 
                    id(e) as edge_id,
                    id(n) as from_id,
                    id(m) as to_id,
                    n.name as from_name,
                    m.name as to_name,
                    n.arango_key as from_key,
                    m.arango_key as to_key,
                    n.kind as from_kind,
                    m.kind as to_kind,
                    e.projects as projects,
                    e.relationType as rel_type
                LIMIT 5000
                """
        else:
            # Определить, является ли start ID или ключом
            if start.isdigit():
                # start - это ID узла
                start_id = int(start)
                if project:
                    query = f"""
                    MATCH (start:canonical_node)
                    WHERE id(start) = {start_id}
                    MATCH path = (start)-[e:project_relation*1..{depth}]->(target)
                    WITH relationships(path) as edges_list, nodes(path) as nodes_list
                    UNWIND range(0, size(edges_list)-1) as i
                    WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
                    WHERE '{project}' IN e.projects
                    RETURN 
                        id(e) as edge_id,
                        id(from_node) as from_id,
                        id(to_node) as to_id,
                        from_node.name as from_name,
                        to_node.name as to_name,
                        from_node.arango_key as from_key,
                        to_node.arango_key as to_key,
                        from_node.kind as from_kind,
                        to_node.kind as to_kind,
                        e.projects as projects,
                        e.relationType as rel_type
                    LIMIT 5000
                    """
                else:
                    query = f"""
                    MATCH (start:canonical_node)
                    WHERE id(start) = {start_id}
                    MATCH path = (start)-[e:project_relation*1..{depth}]->(target)
                    WITH relationships(path) as edges_list, nodes(path) as nodes_list
                    UNWIND range(0, size(edges_list)-1) as i
                    WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
                    RETURN 
                        id(e) as edge_id,
                        id(from_node) as from_id,
                        id(to_node) as to_id,
                        from_node.name as from_name,
                        to_node.name as to_name,
                        from_node.arango_key as from_key,
                        to_node.arango_key as to_key,
                        from_node.kind as from_kind,
                        to_node.kind as to_kind,
                        e.projects as projects,
                        e.relationType as rel_type
                    LIMIT 5000
                    """
            else:
                # start - это ключ узла
                start_key = start.split('/')[-1] if '/' in start else start
                if project:
                    query = f"""
                    MATCH (start:canonical_node {{arango_key: '{start_key}'}})
                    MATCH path = (start)-[e:project_relation*1..{depth}]->(target)
                    WITH relationships(path) as edges_list, nodes(path) as nodes_list
                    UNWIND range(0, size(edges_list)-1) as i
                    WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
                    WHERE '{project}' IN e.projects
                    RETURN 
                        id(e) as edge_id,
                        id(from_node) as from_id,
                        id(to_node) as to_id,
                        from_node.name as from_name,
                        to_node.name as to_name,
                        from_node.arango_key as from_key,
                        to_node.arango_key as to_key,
                        from_node.kind as from_kind,
                        to_node.kind as to_kind,
                        e.projects as projects,
                        e.relationType as rel_type
                    LIMIT 5000
                    """
                else:
                    query = f"""
                    MATCH (start:canonical_node {{arango_key: '{start_key}'}})
                    MATCH path = (start)-[e:project_relation*1..{depth}]->(target)
                    WITH relationships(path) as edges_list, nodes(path) as nodes_list
                    UNWIND range(0, size(edges_list)-1) as i
                    WITH edges_list[i] as e, nodes_list[i] as from_node, nodes_list[i+1] as to_node
                    RETURN 
                        id(e) as edge_id,
                        id(from_node) as from_id,
                        id(to_node) as to_id,
                        from_node.name as from_name,
                        to_node.name as to_name,
                        from_node.arango_key as from_key,
                        to_node.arango_key as to_key,
                        from_node.kind as from_kind,
                        to_node.kind as to_kind,
                        e.projects as projects,
                        e.relationType as rel_type
                    LIMIT 5000
                    """
        
        results = execute_cypher(query)
        
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
    """Получить детали объекта"""
    try:
        doc_id = request.args.get('id', '')
        
        if not doc_id:
            return jsonify({'error': 'Missing "id" parameter'}), 400
        
        # ID может быть числом (AGE id) или строкой (arango_key)
        try:
            node_id = int(doc_id)
            # Поиск по ID
            query = "MATCH (n) WHERE id(n) = $node_id RETURN n"
            params = {'node_id': node_id}
        except ValueError:
            # Поиск по arango_key
            key = doc_id.split('/')[-1] if '/' in doc_id else doc_id
            query = "MATCH (n {arango_key: $key}) RETURN n"
            params = {'key': key}
        
        results = execute_cypher(query, params)
        
        if not results or not results[0][0]:
            return jsonify({'error': f'Document "{doc_id}" not found'}), 404
        
        # Конвертировать agtype в dict
        node_data = agtype_to_python(results[0][0])
        
        return jsonify(node_data)
    except Exception as e:
        log(f"Error in get_object_details: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/expand_node', methods=['GET'])
def expand_node():
    """Получить соседние узлы (родители или потомки) для выбранного узла"""
    try:
        node_id = request.args.get('node_id', '')
        direction = request.args.get('direction', 'outbound')
        project = request.args.get('project', '')
        theme = request.args.get('theme', 'dark')
        
        if not node_id:
            return jsonify({'error': 'Missing "node_id" parameter'}), 400
        
        # Преобразовать node_id
        try:
            nid = int(node_id)
        except:
            key = node_id.split('/')[-1] if '/' in node_id else node_id
            # Получить ID по ключу
            results = execute_cypher("MATCH (n {arango_key: $key}) RETURN id(n)", {'key': key})
            if not results:
                return jsonify({'error': f'Node {node_id} not found'}), 404
            nid = agtype_to_python(results[0][0])
        
        # Cypher запрос в зависимости от направления
        if direction == 'outbound':
            query = """
            MATCH (start)-[e:project_relation]->(end)
            WHERE id(start) = $node_id
            RETURN end as node, e as edge
            """
        else:  # inbound
            query = """
            MATCH (start)<-[e:project_relation]-(end)
            WHERE id(start) = $node_id
            RETURN end as node, e as edge
            """
        
        results = execute_cypher(query, {'node_id': nid})
        
        # Форматирование для vis-network
        nodes = []
        edges = []
        
        for row in results:
            node = agtype_to_python(row[0])
            edge = agtype_to_python(row[1])
            
            if node:
                node_kind = node.get('properties', {}).get('kind', 'unknown')
                
                nodes.append({
                    'id': node.get('id'),
                    'label': node.get('properties', {}).get('name', ''),
                    'shape': 'box' if node_kind == 'concept' else 'ellipse',
                    'color': {
                        'background': '#263238' if theme == 'dark' else '#E3F2FD'
                    } if node_kind == 'concept' else {
                        'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'
                    }
                })
            
            if edge:
                edge_props = edge.get('properties', {})
                edges.append({
                    'id': edge.get('id'),
                    'from': edge.get('start_id'),
                    'to': edge.get('end_id'),
                    'label': ', '.join(edge_props.get('projects', [])) if edge_props.get('projects') else 'альтернатива',
                    'color': {
                        'color': '#64B5F6' if edge_props.get('projects') else '#9E9E9E'
                    }
                })
        
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
        
        # Cypher запрос для подграфа
        if direction == 'outbound':
            query = f"""
            MATCH (start)-[e:project_relation*1..{max_depth}]->(end)
            WHERE id(start) = $node_id
            RETURN id(end) as node_id, id(e) as edge_id
            """
        else:  # inbound
            query = f"""
            MATCH (start)<-[e:project_relation*1..{max_depth}]-(end)
            WHERE id(start) = $node_id
            RETURN id(end) as node_id, id(e) as edge_id
            """
        
        results = execute_cypher(query, {'node_id': nid})
        
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
        
        # TODO: Преобразовать arango-style IDs в AGE IDs
        # Пока используем простое преобразование
        try:
            from_vertex_id = int(from_id)
            to_vertex_id = int(to_id)
        except:
            # Это arango keys, нужно получить AGE IDs
            return jsonify({'success': False, 'error': 'Conversion from arango_key to AGE ID not implemented yet'}), 501
        
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
        
        # TODO: Преобразовать arango IDs в AGE IDs
        try:
            from_vertex_id = int(from_id)
            to_vertex_id = int(to_id)
            exclude_id = int(exclude_edge_id) if exclude_edge_id else None
        except:
            return jsonify({'success': False, 'error': 'ID conversion not implemented'}), 501
        
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
    log("✓ Connected to PostgreSQL")
    
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

