#!/usr/bin/env python3
"""
Dynamic ArangoDB Graph Viewer (local HTTP server)
- Serves an interactive page with controls
- Fetches graph data from this local server with query params
- No file regeneration required; updates happen instantly
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from arango import ArangoClient
import json
import webbrowser
import argparse

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>ArangoDB Graph Viewer (Dynamic)</title>
<script type="text/javascript" src="https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/vis-network@9.1.6/styles/vis-network.min.css" />
<!-- Tom-Select для комбобокса с поиском -->
<link rel="stylesheet" href="/lib/tom-select/tom-select.css" />
<script src="/lib/tom-select/tom-select.complete.min.js"></script>
<style>
  body { margin: 0; background: #111; color: #e0e0e0; font-family: Arial, sans-serif; }
  #controls { position: fixed; top: 10px; left: 10px; background: rgba(0,0,0,0.82); color: white; padding: 12px; border-radius: 8px; z-index: 1000; min-width: 260px; max-width: 320px; }
  #graph { position: absolute; top:0; left:0; right:0; bottom:0; }
  label { font-size: 11px; }
  select, input[type=range], input[list] { width: 100%; }
  .row { margin-bottom: 8px; }
  .btn { padding: 7px; border-radius: 4px; border: none; cursor: pointer; font-size: 12px; }
  .btn-primary { background: #1976D2; color: #fff; }
  .btn-success { background: #43A047; color: #fff; }
</style>
</head>
<body>
<div id="controls">
  <h3 style="margin:0 0 10px 0; font-size:16px">🎛️ Управление графом</h3>
  <div class="row">
    <label>Стартовая вершина:</label>
    <select id="start" placeholder="Начните вводить для поиска..."></select>
  </div>
  <div class="row">
    <label>Глубина обхода:</label>
    <input type="range" id="depth" min="1" max="15" value="5" />
    <span id="depthVal" style="font-size:12px">5</span>
  </div>
  <div class="row">
    <label>Проект:</label>
    <select id="project">
      <option value="">Все проекты</option>
      <option value="fepro">FEPRO</option>
      <option value="femsq">FEMSQ</option>
      <option value="fedoc">FEDOC</option>
    </select>
  </div>
  <div class="row">
    <label>Тема:</label>
    <div>
      <label><input type="radio" name="theme" value="dark" checked> 🌙 Тёмная</label>
      <label style="margin-left:12px"><input type="radio" name="theme" value="light"> ☀️ Светлая</label>
    </div>
  </div>
  <div class="row" style="display:flex; gap:6px;">
    <button class="btn btn-primary" id="reload">🔄 Обновить</button>
    <button class="btn btn-success" id="fit">📐 Подогнать</button>
  </div>
  <div style="font-size:11px; color:#ccc">
    Узлов: <span id="nodeCount">-</span> • Рёбер: <span id="edgeCount">-</span>
  </div>
</div>
<div id="graph"></div>
<script>
  const container = document.getElementById('graph');
  const options = {
    physics: { enabled: true, solver: 'hierarchicalRepulsion', hierarchicalRepulsion: { nodeDistance: 160, springLength: 160, damping: 0.45, avoidOverlap: 1 }, stabilization: { iterations: 800 } },
    layout: { hierarchical: { enabled: true, direction: 'UD', levelSeparation: 140, nodeSpacing: 180, treeSpacing: 240, sortMethod: 'directed', edgeMinimization: true, blockShifting: true, parentCentralization: true } },
    interaction: { navigationButtons: true, keyboard: true, hover: true },
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.5 } }, smooth: { type: 'cubicBezier', forceDirection: 'vertical' }, font: { size: 12, align: 'middle' } },
    nodes: { font: { size: 16 } }
  };
  let network = new vis.Network(container, {nodes:[], edges:[]}, options);
  window.network = network;

  function params() {
    const theme = document.querySelector('input[name="theme"]:checked').value;
    const startValue = tomSelectInstance ? tomSelectInstance.getValue() : 'canonical_nodes/c:backend';
    return new URLSearchParams({
      start: startValue,
      depth: document.getElementById('depth').value,
      project: document.getElementById('project').value,
      theme
    }).toString();
  }

  function applyTheme(theme) {
    document.body.style.background = theme === 'dark' ? '#111' : '#fff';
    document.body.style.color = theme === 'dark' ? '#e0e0e0' : '#000';
    // Adjust node/edge fonts colors via network options
    const labelColor = theme === 'dark' ? '#E0E0E0' : '#212121';
    const edgeColor = theme === 'dark' ? '#B0BEC5' : '#424242';
    network.setOptions({
      nodes: { font: { color: labelColor } },
      edges: { font: { color: labelColor, strokeColor: theme==='dark' ? '#000' : '#fff' }, color: { color: edgeColor } }
    });
  }

  let tomSelectInstance = null;

  async function loadNodes() {
    const project = document.getElementById('project').value;
    const res = await fetch('/nodes' + (project ? ('?project=' + encodeURIComponent(project)) : ''));
    const list = await res.json();
    
    // Подготовить опции для Tom-Select
    const options = list.map(it => ({
      value: it._id,
      text: `${it._key} - ${it.name || ''}`,
      searchText: `${it._key} ${it.name || ''} ${it._id}`
    }));
    
    // Уничтожить старый экземпляр если есть
    if (tomSelectInstance) {
      const currentValue = tomSelectInstance.getValue();
      tomSelectInstance.destroy();
      tomSelectInstance = null;
      
      // Пересоздать Tom-Select с новыми опциями
      tomSelectInstance = new TomSelect('#start', {
        options: options,
        maxOptions: null,
        create: false,
        sortField: 'text',
        searchField: ['text', 'searchText'],
        placeholder: 'Начните вводить для поиска...',
        render: {
          option: function(data, escape) {
            return '<div>' + escape(data.text) + '</div>';
          },
          item: function(data, escape) {
            return '<div>' + escape(data.text) + '</div>';
          }
        }
      });
      
      // Восстановить предыдущее значение
      if (currentValue && options.find(o => o.value === currentValue)) {
        tomSelectInstance.setValue(currentValue, true);
      }
    } else {
      // Первоначальная инициализация Tom-Select
      tomSelectInstance = new TomSelect('#start', {
        options: options,
        maxOptions: null,
        create: false,
        sortField: 'text',
        searchField: ['text', 'searchText'],
        placeholder: 'Начните вводить для поиска...',
        render: {
          option: function(data, escape) {
            return '<div>' + escape(data.text) + '</div>';
          },
          item: function(data, escape) {
            return '<div>' + escape(data.text) + '</div>';
          }
        },
        onInitialize: function() {
          // Установить значение по умолчанию или из URL
          const urlParams = new URLSearchParams(window.location.search);
          const startParam = urlParams.get('start');
          if (startParam) {
            this.setValue(startParam, true);
          } else {
            this.setValue('canonical_nodes/c:backend', true);
          }
        }
      });
    }
  }

  async function load() {
    const q = params();
    const res = await fetch('/graph?' + q);
    const data = await res.json();
    applyTheme(data.theme);
    network.setData({ nodes: new vis.DataSet(data.nodes), edges: new vis.DataSet(data.edges) });
    document.getElementById('nodeCount').textContent = data.nodes.length;
    document.getElementById('edgeCount').textContent = data.edges.length;
  }

  document.getElementById('reload').onclick = load;
  document.getElementById('fit').onclick = () => network.fit();
  document.getElementById('depth').oninput = (e) => document.getElementById('depthVal').textContent = e.target.value;
  document.getElementById('project').onchange = () => loadNodes();

  loadNodes().then(load);

</script>
</body>
</html>
"""

class GraphHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        from pathlib import Path
        parsed = urlparse(self.path)
        
        # Обработка статических файлов Tom-Select
        if self.path.startswith('/lib/tom-select/'):
            file_path = Path(__file__).parent / self.path.lstrip('/')
            if file_path.exists():
                content_type = 'text/css' if file_path.suffix == '.css' else 'application/javascript'
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
        
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
            return
        if parsed.path == '/graph':
            qs = parse_qs(parsed.query)
            start = qs.get('start', ['canonical_nodes/c:backend'])[0]
            try:
                depth = int(qs.get('depth', ['5'])[0])
            except Exception:
                depth = 5
            project = qs.get('project', [''])[0] or None
            theme = qs.get('theme', ['dark'])[0]
            edges = self.server.viewer.fetch_graph(
                graph_name=self.server.graph_name,
                project_filter=project,
                max_nodes=5000,
                start_node=start,
                depth=depth
            )
            # Build nodes and edges for vis
            nodes_map = {}
            vis_edges = []
            for e in edges:
                from_id = e['from_key']
                to_id = e['to_key']
                if from_id not in nodes_map:
                    nodes_map[from_id] = {
                        'id': from_id,
                        'label': e['from_name'],
                        'shape': 'box' if e['from_kind'] == 'concept' else 'ellipse',
                        'color': {'background': '#263238' if theme=='dark' else '#E3F2FD'} if e['from_kind']=='concept' else {'background': '#1B5E20' if theme=='dark' else '#C8E6C9'}
                    }
                if to_id not in nodes_map:
                    nodes_map[to_id] = {
                        'id': to_id,
                        'label': e['to_name'],
                        'shape': 'box' if e['to_kind'] == 'concept' else 'ellipse',
                        'color': {'background': '#263238' if theme=='dark' else '#E3F2FD'} if e['to_kind']=='concept' else {'background': '#1B5E20' if theme=='dark' else '#C8E6C9'}
                    }
                vis_edges.append({
                    'from': from_id,
                    'to': to_id,
                    'label': ', '.join(e['projects']) if e['projects'] else 'альтернатива',
                    'color': {'color': '#64B5F6' if e['projects'] else '#9E9E9E'}
                })
            resp = {
                'theme': theme,
                'nodes': list(nodes_map.values()),
                'edges': vis_edges
            }
            body = json.dumps(resp).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == '/nodes':
            # Return start nodes: all when no project, or only vertices involved in edges for selected project
            qs = parse_qs(parsed.query)
            project = qs.get('project', [''])[0]
            nodes = []
            try:
                if project:
                    query = """
                    LET verts = UNIQUE(
                      FLATTEN([
                        FOR e IN project_relations FILTER @project IN e.projects RETURN [e._from, e._to]
                      ])
                    )
                    FOR vid IN verts
                      LET d = DOCUMENT(vid)
                      FILTER d != null
                      RETURN { _id: d._id, _key: d._key, name: d.name }
                    """
                    cursor = self.server.viewer.db.aql.execute(query, bind_vars={'project': project})
                    nodes = list(cursor)
                else:
                    # all vertices from canonical_nodes and projects
                    cur1 = self.server.viewer.db.aql.execute("FOR d IN canonical_nodes RETURN {_id: d._id, _key: d._key, name: d.name}")
                    nodes.extend(list(cur1))
                    cur2 = self.server.viewer.db.aql.execute("FOR p IN projects RETURN {_id: p._id, _key: p._key, name: p.name}")
                    nodes.extend(list(cur2))
            except Exception:
                pass
            body = json.dumps(nodes).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def serve(host, db, user, password, graph_name, port):
    client = ArangoClient(hosts=host)
    viewer = type('V', (), {})()
    viewer.db = client.db(db, username=user, password=password)
    def fetch_graph(graph_name, project_filter=None, max_nodes=1000, start_node=None, depth=10):
        if not start_node:
            start_node = 'canonical_nodes/c:backend'
        query = """
        FOR v, e IN 1..@depth OUTBOUND @start_node GRAPH @graph
            LIMIT @max_nodes
            RETURN {
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
        bind = {
            'depth': depth,
            'start_node': start_node,
            'graph': graph_name,
            'max_nodes': max_nodes
        }
        if project_filter:
            # Apply filter post-query to avoid query injection (simple filter client-side)
            cursor = viewer.db.aql.execute(query, bind_vars=bind)
            edges = [e for e in cursor if project_filter in (e.get('projects') or [])]
        else:
            cursor = viewer.db.aql.execute(query, bind_vars=bind)
            edges = list(cursor)
        return edges
    viewer.fetch_graph = fetch_graph

    class _Server(HTTPServer):
        pass
    httpd = _Server(('127.0.0.1', port), GraphHandler)
    httpd.viewer = viewer
    httpd.graph_name = graph_name
    url = f"http://127.0.0.1:{port}/"
    print(f"🌐 Serving on {url}")
    webbrowser.open(url)
    httpd.serve_forever()


def main():
    p = argparse.ArgumentParser(description='Dynamic ArangoDB Graph Viewer (local server)')
    p.add_argument('--host', default='http://localhost:8529')
    p.add_argument('--db', default='fedoc')
    p.add_argument('--user', default='root')
    p.add_argument('--password', required=True)
    p.add_argument('--graph', default='common_project_graph')
    p.add_argument('--port', type=int, default=8899)
    args = p.parse_args()
    serve(args.host, args.db, args.user, args.password, args.graph, args.port)

if __name__ == '__main__':
    main()
