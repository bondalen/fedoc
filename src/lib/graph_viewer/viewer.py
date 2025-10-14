#!/usr/bin/env python3
"""
ArangoDB Graph Viewer
Интерактивное desktop приложение для просмотра графов из ArangoDB
"""

from arango import ArangoClient
from pyvis.network import Network
import argparse
import webbrowser
import os
from pathlib import Path

class ArangoGraphViewer:
    def __init__(self, host, database, username, password):
        """Инициализация подключения к ArangoDB"""
        self.client = ArangoClient(hosts=host)
        self.db = self.client.db(database, username=username, password=password)
        
    def fetch_graph(self, graph_name, project_filter=None, max_nodes=1000, start_node=None, depth=10):
        """Получить граф из ArangoDB от стартовой вершины на заданную глубину"""
        print(f"🔍 Загрузка графа '{graph_name}' из ArangoDB...")
        
        if not start_node:
            start_node = 'canonical_nodes/c:backend'
        
        # Построить AQL запрос
        query = """
        FOR v, e IN 1..@depth OUTBOUND @start_node
            GRAPH @graph_name
        """
        
        if project_filter:
            query += " FILTER @project IN e.projects"
        
        query += """
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
        
        # Выполнить запрос
        bind_vars = {
            'start_node': start_node,
            'depth': depth,
            'graph_name': graph_name,
            'max_nodes': max_nodes
        }
        if project_filter:
            bind_vars['project'] = project_filter
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        edges = list(cursor)
        print(f"✅ Загружено {len(edges)} рёбер")
        
        return edges
    
    def visualize(self, edges, output_file='graph.html', project_filter=None, theme='dark'):
        """Создать интерактивную визуализацию"""
        print(f"🎨 Создание визуализации...")
        
        # Темы
        if theme == 'dark':
            bgcolor = '#111111'
            font_color = '#e0e0e0'
            concept_color = '#1E88E5'
            tech_color = '#43A047'
            edge_real = '#64B5F6'
            edge_alt = '#9E9E9E'
            node_concept_bg = '#263238'
            node_tech_bg = '#1B5E20'
        else:
            bgcolor = '#ffffff'
            font_color = '#000000'
            concept_color = '#1565C0'
            tech_color = '#2E7D32'
            edge_real = '#1976D2'
            edge_alt = '#9E9E9E'
            node_concept_bg = '#E3F2FD'
            node_tech_bg = '#C8E6C9'
        
        # Создать сеть
        net = Network(
            height='900px',
            width='100%',
            bgcolor=bgcolor,
            font_color=font_color,
            directed=True
        )
        
        # Настройки физики и укладки: компактнее + сглаживание рёбер
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "solver": "hierarchicalRepulsion",
            "stabilization": { "enabled": true, "iterations": 800, "updateInterval": 25 },
            "hierarchicalRepulsion": {
              "nodeDistance": 160,
              "springLength": 160,
              "springConstant": 0.03,
              "damping": 0.45,
              "avoidOverlap": 1
            },
            "minVelocity": 0.5
          },
          "nodes": {
            "font": { "size": 16, "face": "Arial" },
            "borderWidth": 2,
            "size": 25
          },
          "edges": {
            "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } },
            "smooth": { "type": "cubicBezier", "forceDirection": "vertical" },
            "font": { "size": 12, "align": "middle" }
          },
          "interaction": {
            "navigationButtons": true,
            "keyboard": true,
            "hover": true,
            "zoomView": true,
            "dragView": true
          },
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 140,
              "nodeSpacing": 180,
              "treeSpacing": 240,
              "blockShifting": true,
              "edgeMinimization": true,
              "parentCentralization": true
            }
          }
        }
        """)
        
        # Добавить узлы и рёбра
        added_nodes = set()
        
        for edge in edges:
            # Определить цвета для узлов
            from_color = node_concept_bg if edge['from_kind'] == 'concept' else node_tech_bg
            to_color = node_concept_bg if edge['to_kind'] == 'concept' else node_tech_bg
            
            # Добавить узлы
            if edge['from_key'] not in added_nodes:
                net.add_node(
                    edge['from_key'],
                    label=edge['from_name'],
                    color=from_color,
                    title=f"{edge['from_key']}\nТип: {edge['from_kind']}",
                    shape='box' if edge['from_kind'] == 'concept' else 'ellipse'
                )
                added_nodes.add(edge['from_key'])
            
            if edge['to_key'] not in added_nodes:
                net.add_node(
                    edge['to_key'],
                    label=edge['to_name'],
                    color=to_color,
                    title=f"{edge['to_key']}\nТип: {edge['to_kind']}",
                    shape='box' if edge['to_kind'] == 'concept' else 'ellipse'
                )
                added_nodes.add(edge['to_key'])
            
            # Добавить ребро
            projects_label = ', '.join(edge['projects']) if edge['projects'] else 'альтернатива'
            net.add_edge(
                edge['from_key'],
                edge['to_key'],
                label=projects_label,
                title=f"{edge['type']}: {projects_label}",
                color=edge_real if edge['projects'] else edge_alt
            )
        
        # Добавить панель управления в HTML
        html_content = net.generate_html()
        
        # Вставить контролы перед закрытием body
        controls_html = """
        <div id="controls" style="position: fixed; top: 10px; left: 10px; background: rgba(0,0,0,0.8); color: white; padding: 15px; border-radius: 8px; font-family: Arial; z-index: 1000; min-width: 300px;">
            <h3 style="margin: 0 0 10px 0; font-size: 16px;">🎛️ Управление графом</h3>
            
            <div style="margin-bottom: 10px;">
                <label style="display: block; margin-bottom: 5px; font-size: 12px;">Стартовая вершина:</label>
                <select id="startNode" style="width: 100%; padding: 5px; border-radius: 4px; border: 1px solid #ccc;">
                    <option value="canonical_nodes/c:backend">c:backend (Бэкенд)</option>
                    <option value="canonical_nodes/c:development-objects">c:development-objects (Объекты разработки)</option>
                    <option value="canonical_nodes/c:layer">c:layer (Слой)</option>
                    <option value="canonical_nodes/c:frontend">c:frontend (Фронтенд)</option>
                    <option value="canonical_nodes/t:java@21">t:java@21 (Java 21)</option>
                    <option value="canonical_nodes/t:spring-boot@3.4.5">t:spring-boot@3.4.5 (Spring Boot)</option>
                </select>
            </div>
            
            <div style="margin-bottom: 10px;">
                <label style="display: block; margin-bottom: 5px; font-size: 12px;">Глубина обхода:</label>
                <input type="range" id="depth" min="1" max="15" value="5" style="width: 100%;">
                <span id="depthValue" style="font-size: 12px;">5</span>
            </div>
            
            <div style="margin-bottom: 10px;">
                <label style="display: block; margin-bottom: 5px; font-size: 12px;">Проект:</label>
                <select id="project" style="width: 100%; padding: 5px; border-radius: 4px; border: 1px solid #ccc;">
                    <option value="">Все проекты</option>
                    <option value="fepro">FEPRO</option>
                    <option value="femsq">FEMSQ</option>
                    <option value="fedoc">FEDOC</option>
                </select>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-size: 12px;">Тема:</label>
                <div style="display: flex; gap: 10px;">
                    <label style="display: flex; align-items: center; font-size: 12px;">
                        <input type="radio" name="theme" value="dark" checked style="margin-right: 5px;">
                        🌙 Тёмная
                    </label>
                    <label style="display: flex; align-items: center; font-size: 12px;">
                        <input type="radio" name="theme" value="light" style="margin-right: 5px;">
                        ☀️ Светлая
                    </label>
                </div>
            </div>
            
            <div style="display: flex; gap: 5px;">
                <button id="updateGraph" style="flex: 1; padding: 8px; background: #1976D2; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    🔄 Обновить
                </button>
                <button id="fitGraph" style="flex: 1; padding: 8px; background: #43A047; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                    📐 Подогнать
                </button>
            </div>
            
            <div style="margin-top: 10px; font-size: 11px; color: #ccc;">
                <div>Узлов: <span id="nodeCount">-</span></div>
                <div>Рёбер: <span id="edgeCount">-</span></div>
            </div>
        </div>
        
        <script>
        // Обновить граф
        document.getElementById('updateGraph').onclick = function() {
            const startNode = document.getElementById('startNode').value;
            const depth = document.getElementById('depth').value;
            const project = document.getElementById('project').value;
            const theme = document.querySelector('input[name="theme"]:checked').value;
            
            // Перезагрузить страницу с новыми параметрами
            const url = new URL(window.location);
            url.searchParams.set('start', startNode);
            url.searchParams.set('depth', depth);
            url.searchParams.set('project', project);
            url.searchParams.set('theme', theme);
            window.location.href = url.toString();
        };
        
        // Подогнать граф
        document.getElementById('fitGraph').onclick = function() {
            if (window.network) {
                window.network.fit();
            }
        };
        
        // Обновить значение глубины
        document.getElementById('depth').oninput = function() {
            document.getElementById('depthValue').textContent = this.value;
        };
        
        // Загрузить параметры из URL
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('start')) document.getElementById('startNode').value = urlParams.get('start');
        if (urlParams.get('depth')) {
            document.getElementById('depth').value = urlParams.get('depth');
            document.getElementById('depthValue').textContent = urlParams.get('depth');
        }
        if (urlParams.get('project')) document.getElementById('project').value = urlParams.get('project');
        if (urlParams.get('theme')) document.querySelector('input[name="theme"][value="' + urlParams.get('theme') + '"]').checked = true;
        
        // Обновить счётчики
        setTimeout(() => {
            if (window.network) {
                const nodes = window.network.getNodes();
                const edges = window.network.getEdges();
                document.getElementById('nodeCount').textContent = nodes.length;
                document.getElementById('edgeCount').textContent = edges.length;
            }
        }, 1000);
        </script>
        """
        
        # Вставить контролы перед </body>
        html_content = html_content.replace('</body>', controls_html + '</body>')
        
        # Сохранить обновлённый HTML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Сохранено в: {output_file}")
        print(f"✅ Узлов: {len(added_nodes)}")
        print(f"✅ Рёбер: {len(edges)}")
        
        return output_file


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='ArangoDB Graph Viewer - интерактивный просмотр графов'
    )
    parser.add_argument('--host', default='http://localhost:8529', help='Хост ArangoDB')
    parser.add_argument('--db', default='fedoc', help='База данных')
    parser.add_argument('--user', default='root', help='Пользователь')
    parser.add_argument('--password', required=True, help='Пароль')
    parser.add_argument('--graph', default='common_project_graph', help='Имя графа')
    parser.add_argument('--project', help='Фильтр по проекту (fepro, femsq, fedoc)')
    parser.add_argument('--output', default='/tmp/arango-graph.html', help='Выходной HTML файл')
    parser.add_argument('--max-nodes', type=int, default=1000, help='Максимум узлов')
    parser.add_argument('--start-node', help='Стартовая вершина, например canonical_nodes/c:backend')
    parser.add_argument('--depth', type=int, default=10, help='Глубина обхода (рёбер)')
    parser.add_argument('--theme', choices=['dark','light'], default='dark', help='Тема оформления')
    parser.add_argument('--no-browser', action='store_true', help='Не открывать браузер')
    
    args = parser.parse_args()
    
    try:
        # Подключиться к ArangoDB
        print(f"🔌 Подключение к {args.host}/{args.db}...")
        viewer = ArangoGraphViewer(args.host, args.db, args.user, args.password)
        
        # Загрузить граф
        edges = viewer.fetch_graph(
            graph_name=args.graph,
            project_filter=args.project,
            max_nodes=args.max_nodes,
            start_node=args.start_node,
            depth=args.depth
        )
        
        if not edges:
            print("⚠️  Граф пуст или не найден")
            return
        
        # Создать визуализацию
        output_file = viewer.visualize(edges, args.output, args.project, theme=args.theme)
        
        # Открыть в браузере
        if not args.no_browser:
            print(f"🌐 Открытие в браузере...")
            webbrowser.open('file://' + os.path.abspath(output_file))
        
        print(f"\n✅ Готово! Граф открыт в браузере.")
        print(f"📁 Файл: {output_file}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

