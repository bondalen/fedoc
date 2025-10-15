#!/usr/bin/env python3
"""
API сервер для graph viewer frontend
Предоставляет REST API endpoints для фронтенд-приложения
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from arango import ArangoClient
import json
import argparse

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/nodes':
            self.handle_nodes(parsed)
        elif parsed.path == '/graph':
            self.handle_graph(parsed)
        elif parsed.path == '/object_details':
            self.handle_object_details(parsed)
        else:
            self.send_error(404, 'Not found')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def handle_nodes(self, parsed):
        """Вернуть список узлов"""
        try:
            qs = parse_qs(parsed.query)
            project = qs.get('project', [''])[0]
            
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
                cursor = self.server.db.aql.execute(query, bind_vars={'project': project})
            else:
                query = "FOR d IN canonical_nodes RETURN {_id: d._id, _key: d._key, name: d.name}"
                cursor = self.server.db.aql.execute(query)
            
            result = list(cursor)
            self.send_json_response(result)
        except Exception as e:
            self.send_error(500, f'Error: {str(e)}')
    
    def handle_graph(self, parsed):
        """Построить граф"""
        try:
            qs = parse_qs(parsed.query)
            start = qs.get('start', ['canonical_nodes/c:backend'])[0]
            depth = int(qs.get('depth', ['5'])[0])
            project = qs.get('project', [''])[0] or None
            theme = qs.get('theme', ['dark'])[0]
            
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
            
            cursor = self.server.db.aql.execute(query, bind_vars=bind_vars)
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
            
            self.send_json_response(result)
        except Exception as e:
            self.send_error(500, f'Error: {str(e)}')
    
    def handle_object_details(self, parsed):
        """Получить детали объекта"""
        try:
            qs = parse_qs(parsed.query)
            doc_id = qs.get('id', [''])[0]
            
            if not doc_id:
                self.send_error(400, 'Missing "id" parameter')
                return
            
            query = "RETURN DOCUMENT(@id)"
            cursor = self.server.db.aql.execute(query, bind_vars={'id': doc_id})
            result = list(cursor)
            
            if not result or result[0] is None:
                self.send_error(404, f'Document "{doc_id}" not found')
                return
            
            self.send_json_response(result[0])
        except Exception as e:
            self.send_error(500, f'Error: {str(e)}')
    
    def send_json_response(self, data):
        """Отправить JSON ответ"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

def main():
    parser = argparse.ArgumentParser(description='Graph Viewer API Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host')
    parser.add_argument('--port', type=int, default=8899, help='Port')
    parser.add_argument('--db-host', default='http://localhost:8529', help='ArangoDB host')
    parser.add_argument('--db-name', default='fedoc', help='Database name')
    parser.add_argument('--db-user', default='root', help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    args = parser.parse_args()
    
    # Подключение к ArangoDB
    print(f"Connecting to ArangoDB at {args.db_host}...")
    client = ArangoClient(hosts=args.db_host)
    db = client.db(args.db_name, username=args.db_user, password=args.db_password)
    print("✓ Connected to ArangoDB")
    
    # Сохраняем db в сервере для доступа из обработчиков
    class _Server(HTTPServer):
        pass
    
    server = _Server((args.host, args.port), APIHandler)
    server.db = db
    
    print(f"🌐 API Server running on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
        server.shutdown()

if __name__ == '__main__':
    main()

