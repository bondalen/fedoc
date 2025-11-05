"""
Построение подграфа проекта из PostgreSQL + Apache AGE

Извлекает только рёбра и узлы, относящиеся к конкретному проекту.
"""

import json
from collections import defaultdict
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor


class Subgraph:
    """Подграф проекта с узлами и рёбрами"""
    
    def __init__(self, nodes: Dict[int, Dict], adjacency: Dict[int, List[Dict]]):
        """
        Args:
            nodes: Словарь {node_id: node_data}
            adjacency: Словарь {node_id: [{'to': node_id, 'type': str, 'projects': list}]}
        """
        self.nodes = nodes
        self.adjacency = adjacency
    
    def get_node(self, node_id: int) -> Optional[Dict]:
        """Получить узел по ID"""
        return self.nodes.get(node_id)
    
    def get_node_by_key(self, arango_key: str) -> Optional[Dict]:
        """Получить узел по arango_key"""
        for node_id, node in self.nodes.items():
            if node.get('arango_key') == arango_key:
                return {'id': node_id, **node}
        return None
    
    def get_children(self, node_id: int) -> List[Dict]:
        """Получить дочерние узлы"""
        return self.adjacency.get(node_id, [])
    
    def find_root_nodes(self) -> List[int]:
        """Найти корневые узлы (без входящих рёбер в подграфе)"""
        nodes_with_parents = set()
        for children in self.adjacency.values():
            for child in children:
                nodes_with_parents.add(child['to'])
        
        return [node_id for node_id in self.nodes.keys() if node_id not in nodes_with_parents]
    
    def stats(self) -> Dict[str, int]:
        """Статистика подграфа"""
        edge_count = sum(len(children) for children in self.adjacency.values())
        return {
            'nodes': len(self.nodes),
            'edges': edge_count,
            'root_nodes': len(self.find_root_nodes())
        }


class SubgraphBuilder:
    """Построение подграфа проекта из БД"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Args:
            db_config: Конфигурация подключения к БД
                {
                    'host': 'localhost',
                    'port': 15432,
                    'database': 'fedoc',
                    'user': 'postgres',
                    'password': '...'
                }
        """
        self.db_config = db_config
        self.graph_name = 'common_project_graph'
    
    def build(self, project_key: str) -> Subgraph:
        """
        Построить подграф проекта
        
        Args:
            project_key: Ключ проекта (fedoc, fepro, femsq)
            
        Returns:
            Subgraph с узлами и рёбрами проекта
            
        Raises:
            psycopg2.Error: Ошибка подключения к БД
            ValueError: Проект не найден
        """
        conn = psycopg2.connect(**self.db_config)
        
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Загрузить AGE
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Получить project_id для фильтрации
            cur.execute("""
                SELECT id FROM public.projects WHERE key = %s;
            """, (project_key,))
            project_result = cur.fetchone()
            
            if not project_result:
                raise ValueError(f"Проект '{project_key}' не найден в таблице projects")
            
            project_id = project_result['id']
            
            # Получить все рёбра проекта через JOIN с edge_projects
            # Новая архитектура: проекты хранятся в таблице edge_projects, а не в свойствах рёбер
            # Используем двухшаговый подход: сначала получаем edge_id из таблицы, затем фильтруем Cypher
            query = f"""
                WITH project_edges AS (
                    SELECT edge_id FROM public.edge_projects WHERE project_id = {project_id}
                )
                SELECT DISTINCT
                    cypher_result.from_id::text as from_id, 
                    cypher_result.from_key as from_key,
                    cypher_result.from_name as from_name,
                    cypher_result.edge_type as edge_type,
                    cypher_result.to_id::text as to_id,
                    cypher_result.to_key as to_key,
                    cypher_result.to_name as to_name
                FROM (
                    SELECT * FROM cypher('{self.graph_name}', $$
                      MATCH (a)-[r]->(b)
                      RETURN id(a) as from_id, 
                             a.arango_key as from_key,
                             a.name as from_name,
                             type(r) as edge_type,
                             id(r) as edge_id,
                             id(b) as to_id,
                             b.arango_key as to_key,
                             b.name as to_name
                    $$) as (from_id agtype, from_key agtype, from_name agtype,
                            edge_type agtype, edge_id agtype,
                            to_id agtype, to_key agtype, to_name agtype)
                ) cypher_result
                INNER JOIN project_edges pe ON pe.edge_id = cypher_result.edge_id::text::bigint;
            """
            
            cur.execute(query)
            
            rows = cur.fetchall()
            if not rows:
                raise ValueError(f"Проект '{project_key}' не найден или не имеет рёбер (запрос вернул 0 строк, project_id={project_id})")
            
            nodes = {}
            adjacency = defaultdict(list)
            rows_processed = 0
            
            try:
                for row in rows:
                    rows_processed += 1
                    try:
                        # Парсинг данных (теперь уже преобразованные через JOIN)
                        from_id = int(row['from_id'])
                        from_key = self._parse_agtype(row['from_key'])
                        from_name = self._parse_agtype(row['from_name'])
                        
                        edge_type = self._parse_agtype(row['edge_type'])
                        
                        to_id = int(row['to_id'])
                        to_key = self._parse_agtype(row['to_key'])
                        to_name = self._parse_agtype(row['to_name'])
                        
                        # Сохранить узлы (базовая информация)
                        if from_id not in nodes:
                            nodes[from_id] = {
                                'arango_key': from_key,
                                'name': from_name
                            }
                        
                        if to_id not in nodes:
                            nodes[to_id] = {
                                'arango_key': to_key,
                                'name': to_name
                            }
                        
                        # Сохранить ребро
                        adjacency[from_id].append({
                            'to': to_id,
                            'type': edge_type,
                            'projects': [project_key]  # Добавляем для совместимости
                        })
                    except Exception as row_error:
                        raise ValueError(f"Ошибка при обработке строки #{rows_processed}: {row_error}")
            except Exception as e:
                raise ValueError(f"Ошибка при обработке строки #{rows_processed}: {e}")
            
            if not nodes:
                raise ValueError(f"Проект '{project_key}': обработано {rows_processed} строк, но не создано ни одного узла")
            
            # Получить детальную информацию об узлах
            self._enrich_nodes(cur, nodes)
            
            if not nodes:
                raise ValueError(f"Проект '{project_key}': узлы были созданы, но пропали после _enrich_nodes")
            
            return Subgraph(nodes=nodes, adjacency=dict(adjacency))
            
        finally:
            conn.close()
    
    def _parse_agtype(self, value: str) -> Any:
        """
        Парсинг AGE agtype значения
        
        AGE возвращает значения в формате JSON-строк
        """
        if value is None:
            return None
        
        # AGE возвращает строки вида: "value" или [array] или 123
        value_str = str(value)
        
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            # Если не JSON, вернуть как есть
            return value_str
    
    def _enrich_nodes(self, cur, nodes: Dict[int, Dict]):
        """
        Обогатить узлы детальной информацией из БД
        
        Получает дополнительные свойства: kind, description, port, stack, version, status
        """
        for node_id, node_data in nodes.items():
            arango_key = node_data['arango_key']
            
            try:
                # Запрос полной информации об узле
                query = f"""
                    SELECT * FROM cypher('{self.graph_name}', $$
                      MATCH (n {{arango_key: '{arango_key}'}})
                      RETURN n
                    $$) as (node agtype);
                """
                
                cur.execute(query)
                result = cur.fetchone()
                
                if result and result['node']:
                    # Парсинг AGE vertex
                    node_str = str(result['node'])
                    
                    # AGE возвращает строку вида: {...}::vertex
                    if '::vertex' in node_str:
                        node_str = node_str.replace('::vertex', '')
                    
                    node_full = json.loads(node_str)
                    
                    if 'properties' in node_full:
                        props = node_full['properties']
                        
                        # Добавить значимые свойства
                        node_data['kind'] = props.get('kind', props.get('node_type', 'unknown'))
                        node_data['description'] = props.get('description', '')
                        
                        # Дополнительные свойства
                        if 'port' in props:
                            node_data['port'] = props['port']
                        if 'stack' in props:
                            node_data['stack'] = props['stack']
                        if 'version' in props:
                            node_data['version'] = props['version']
                        if 'status' in props:
                            node_data['status'] = props['status']
                        if 'slug' in props:
                            node_data['slug'] = props['slug']
                        
            except Exception as e:
                # Если не удалось получить детали, продолжаем с базовой информацией
                print(f"Warning: Could not enrich node {arango_key}: {e}", file=__import__('sys').stderr)
                node_data['kind'] = 'unknown'
                node_data['description'] = ''

