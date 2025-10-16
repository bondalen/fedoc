#!/usr/bin/env python3
"""
API сервер для graph viewer frontend
Предоставляет REST API endpoints и WebSocket для фронтенд-приложения

Версия 2.0 с поддержкой WebSocket для двусторонней связи
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from arango import ArangoClient
import argparse
import sys
import time
import threading

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
db = None  # ArangoDB connection
_selection_response = None  # Последний ответ от браузера
_selection_lock = threading.Lock()  # Блокировка для thread-safe доступа


# ========== REST API ENDPOINTS ==========

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Вернуть список узлов"""
    try:
        project = request.args.get('project', '')
        
        if project:
            query = """
            LET verts = (
              FOR e IN project_relations 
              FILTER @project IN e.projects 
              RETURN [e._from, e._to]
            )
            LET flattened = FLATTEN(verts)
            LET unique_verts = UNIQUE(flattened)
            FOR vid IN unique_verts
              LET d = DOCUMENT(vid)
              FILTER d != null
              RETURN { _id: d._id, _key: d._key, name: d.name }
            """
            cursor = db.aql.execute(query, bind_vars={'project': project})
        else:
            query = "FOR d IN canonical_nodes RETURN {_id: d._id, _key: d._key, name: d.name}"
            cursor = db.aql.execute(query)
        
        result = list(cursor)
        return jsonify(result)
    except Exception as e:
        log(f"Error in get_nodes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Построить граф"""
    try:
        start = request.args.get('start', 'canonical_nodes/c:backend')
        depth = int(request.args.get('depth', '5'))
        project = request.args.get('project', '') or None
        theme = request.args.get('theme', 'dark')
        
        # AQL запрос для получения графа
        query = """
        FOR v, e IN 1..@depth OUTBOUND @start_node GRAPH @graph
            LIMIT @max_nodes
            RETURN {
                edge_id: e._id,
                from: e._from,
                to: e._to,
                from_name: DOCUMENT(e._from).name,
                to_name: DOCUMENT(e._to).name,
                from_key: DOCUMENT(e._from)._key,
                to_key: DOCUMENT(e._to)._key,
                from_kind: DOCUMENT(e._from).kind,
                to_kind: DOCUMENT(e._to).kind,
                projects: e.projects,
                type: e.relationType
            }
        """
        
        bind_vars = {
            'start_node': start,
            'depth': depth,
            'graph': 'common_project_graph',
            'max_nodes': 5000
        }
        
        cursor = db.aql.execute(query, bind_vars=bind_vars)
        edges = list(cursor)
        
        # Фильтрация по проекту (если указан)
        if project:
            edges = [e for e in edges if project in (e.get('projects') or [])]
        
        # Построение узлов и рёбер для vis-network
        nodes_map = {}
        edges_map = {}  # Используем словарь для устранения дубликатов
        
        for e in edges:
            from_id = e['from']
            to_id = e['to']
            edge_id = e['edge_id']
            
            if from_id not in nodes_map:
                nodes_map[from_id] = {
                    'id': from_id,
                    'label': e['from_name'],
                    'shape': 'box' if e['from_kind'] == 'concept' else 'ellipse',
                    'color': {'background': '#263238' if theme == 'dark' else '#E3F2FD'} if e['from_kind'] == 'concept' else {'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'}
                }
            
            if to_id not in nodes_map:
                nodes_map[to_id] = {
                    'id': to_id,
                    'label': e['to_name'],
                    'shape': 'box' if e['to_kind'] == 'concept' else 'ellipse',
                    'color': {'background': '#263238' if theme == 'dark' else '#E3F2FD'} if e['to_kind'] == 'concept' else {'background': '#1B5E20' if theme == 'dark' else '#C8E6C9'}
                }
            
            # Используем словарь для устранения дубликатов
            if edge_id not in edges_map:
                edges_map[edge_id] = {
                    'id': edge_id,
                    'from': from_id,
                    'to': to_id,
                    'label': ', '.join(e['projects']) if e['projects'] else 'альтернатива',
                    'color': {'color': '#64B5F6' if e['projects'] else '#9E9E9E'}
                }
        
        result = {
            'theme': theme,
            'nodes': list(nodes_map.values()),
            'edges': list(edges_map.values())
        }
        
        return jsonify(result)
    except Exception as e:
        log(f"Error in get_graph: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/object_details', methods=['GET'])
def get_object_details():
    """Получить детали объекта"""
    try:
        doc_id = request.args.get('id', '')
        
        if not doc_id:
            return jsonify({'error': 'Missing "id" parameter'}), 400
        
        query = "RETURN DOCUMENT(@id)"
        cursor = db.aql.execute(query, bind_vars={'id': doc_id})
        result = list(cursor)
        
        if not result or result[0] is None:
            return jsonify({'error': f'Document "{doc_id}" not found'}), 404
        
        return jsonify(result[0])
    except Exception as e:
        log(f"Error in get_object_details: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/request_selection', methods=['GET'])
def request_selection_endpoint():
    """
    Endpoint для MCP команды: запросить выборку у браузера через WebSocket
    
    Вызывается из graph_viewer_manager.get_selected_nodes()
    """
    try:
        timeout = float(request.args.get('timeout', '3.0'))
        
        # Запросить выборку у браузера
        selection = request_selection_from_browser(timeout=timeout)
        
        if selection is None:
            return jsonify({
                'status': 'timeout',
                'message': 'Браузер не ответил в течение заданного времени. Возможно, Graph Viewer не открыт.'
            }), 408  # Request Timeout
        
        return jsonify({
            'status': 'success',
            'selection': selection
        })
        
    except Exception as e:
        log(f"Error in request_selection_endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


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
    """
    Обработка ответа от браузера с текущей выборкой
    
    Вызывается когда браузер отвечает на запрос 'request_selection'
    """
    global _selection_response
    
    with _selection_lock:
        _selection_response = data
        log(f"✓ Received selection from browser: {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")


# ========== ФУНКЦИИ ДЛЯ MCP ==========

def request_selection_from_browser(timeout=3.0):
    """
    Запросить текущую выборку у браузера через WebSocket
    
    Эта функция вызывается из MCP команды get_selected_nodes()
    
    Args:
        timeout: Время ожидания ответа в секундах
    
    Returns:
        dict: Данные выборки или None при таймауте
    """
    global _selection_response
    
    # Сбросить предыдущий ответ
    with _selection_lock:
        _selection_response = None
    
    log("→ Requesting selection from browser...")
    
    # Отправить запрос всем подключенным клиентам
    socketio.emit('request_selection', {'timestamp': time.time()})
    
    # Ждать ответа с таймаутом
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        with _selection_lock:
            if _selection_response is not None:
                log("✓ Selection received from browser")
                return _selection_response
        time.sleep(0.05)  # Проверять каждые 50ms
    
    log("✗ Timeout waiting for selection from browser")
    return None


# ========== MAIN ==========

def main():
    parser = argparse.ArgumentParser(description='Graph Viewer API Server with WebSocket')
    parser.add_argument('--host', default='127.0.0.1', help='Host')
    parser.add_argument('--port', type=int, default=8899, help='Port')
    parser.add_argument('--db-host', default='http://localhost:8529', help='ArangoDB host')
    parser.add_argument('--db-name', default='fedoc', help='Database name')
    parser.add_argument('--db-user', default='root', help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    args = parser.parse_args()
    
    # Подключение к ArangoDB
    log(f"Connecting to ArangoDB at {args.db_host}...")
    client = ArangoClient(hosts=args.db_host)
    
    global db
    db = client.db(args.db_name, username=args.db_user, password=args.db_password)
    log("✓ Connected to ArangoDB")
    
    # Запуск сервера
    log(f"🌐 API Server (Flask + SocketIO) running on http://{args.host}:{args.port}")
    log("📡 WebSocket endpoint: ws://{args.host}:{args.port}/socket.io/")
    log("Press Ctrl+C to stop")
    
    try:
        socketio.run(app, host=args.host, port=args.port, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        log("\n✓ Server stopped")


if __name__ == '__main__':
    main()
