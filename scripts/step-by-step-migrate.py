#!/usr/bin/env python3
"""Пошаговая миграция данных из JSON в PostgreSQL AGE"""

import json
import subprocess
import sys

def run_sql(sql_command):
    """Выполнить SQL команду в PostgreSQL"""
    cmd = [
        'docker', 'exec', 'fedoc-postgres-age', 
        'psql', '-U', 'postgres', '-d', 'fedoc', '-c', sql_command
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}")
        return None
    return result.stdout

def dict_to_cypher_map(d):
    """Конвертировать Python dict в Cypher map формат"""
    if not d:
        return '{}'
    
    def format_value(v):
        if v is None:
            return 'null'
        elif isinstance(v, bool):
            return 'true' if v else 'false'
        elif isinstance(v, (int, float)):
            return str(v)
        elif isinstance(v, str):
            escaped = v.replace("'", "\\'")
            return f"'{escaped}'"
        elif isinstance(v, list):
            items = [format_value(item) for item in v]
            return '[' + ', '.join(items) + ']'
        elif isinstance(v, dict):
            return dict_to_cypher_map(v)
        else:
            escaped = str(v).replace("'", "\\'")
            return f"'{escaped}'"
    
    items = []
    for k, v in d.items():
        items.append(f"{k}: {format_value(v)}")
    
    return '{' + ', '.join(items) + '}'

def main():
    print("🔄 Начинаю пошаговую миграцию данных...")
    
    # Загрузить данные
    with open('/tmp/arango_data.json', 'r') as f:
        data = json.load(f)
    
    nodes = data['nodes']
    edges = data['edges']
    
    print(f"📦 Найдено узлов: {len(nodes)}")
    print(f"🔗 Найдено рёбер: {len(edges)}")
    
    # Настроить AGE
    print("⚙️  Настройка AGE...")
    run_sql("LOAD 'age';")
    run_sql("SET search_path = ag_catalog, public;")
    
    # Мигрировать узлы по одному
    print("📦 Миграция узлов...")
    id_mapping = {}
    
    for i, node in enumerate(nodes):
        arango_id = node['_id']
        arango_key = node['_key']
        
        # Подготовить свойства
        properties = {k: v for k, v in node.items() if not k.startswith('_')}
        properties['arango_key'] = arango_key
        
        props_cypher = dict_to_cypher_map(properties)
        
        # Создать узел
        sql = f"SELECT * FROM cypher('common_project_graph', $$ CREATE (n:canonical_node {props_cypher}) RETURN id(n) $$) as (id agtype)"
        
        result = run_sql(sql)
        if result and 'id' in result:
            # Извлечь ID из результата
            lines = result.strip().split('\n')
            for line in lines:
                if 'id' in line and '|' in line and not 'agtype' in line:
                    try:
                        parts = line.split('|')
                        if len(parts) > 1:
                            age_id = int(parts[1].strip())
                            id_mapping[arango_id] = age_id
                            break
                    except:
                        pass
        
        if (i + 1) % 5 == 0:
            print(f"   Прогресс узлов: {i + 1}/{len(nodes)}")
    
    print(f"✓ Мигрировано узлов: {len(id_mapping)}")
    
    # Мигрировать рёбра
    print("🔗 Миграция рёбер...")
    migrated_edges = 0
    
    for i, edge in enumerate(edges):
        from_arango = edge['_from']
        to_arango = edge['_to']
        
        if from_arango not in id_mapping or to_arango not in id_mapping:
            continue
        
        from_age = id_mapping[from_arango]
        to_age = id_mapping[to_arango]
        
        # Подготовить свойства
        properties = {k: v for k, v in edge.items() if not k.startswith('_')}
        props_cypher = dict_to_cypher_map(properties)
        
        # Создать ребро
        sql = f"SELECT * FROM cypher('common_project_graph', $$ MATCH (a), (b) WHERE id(a) = {from_age} AND id(b) = {to_age} CREATE (a)-[e:project_relation {props_cypher}]->(b) RETURN id(e) $$) as (id agtype)"
        
        result = run_sql(sql)
        if result and 'id' in result:
            migrated_edges += 1
        
        if (i + 1) % 5 == 0:
            print(f"   Прогресс рёбер: {i + 1}/{len(edges)}")
    
    print(f"✓ Мигрировано рёбер: {migrated_edges}")
    
    # Проверить результат
    print("🔍 Проверка результатов...")
    result = run_sql("SELECT * FROM cypher('common_project_graph', $$ MATCH (n) RETURN count(n) $$) as (cnt agtype)")
    print(f"Итоговое количество узлов: {result}")
    
    result = run_sql("SELECT * FROM cypher('common_project_graph', $$ MATCH ()-[e]->() RETURN count(e) $$) as (cnt agtype)")
    print(f"Итоговое количество рёбер: {result}")
    
    print("✅ Миграция завершена!")

if __name__ == '__main__':
    main()
