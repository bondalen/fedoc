#!/usr/bin/env python3
"""Проверка текущих данных в ArangoDB"""

from urllib.request import urlopen, Request
import json

def query_aql(query):
    url = 'http://localhost:8529/_db/fedoc/_api/cursor'
    data = json.dumps({'query': query}).encode()
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req) as response:
        return json.loads(response.read())

# Подсчёт вершин
result = query_aql('FOR d IN canonical_nodes RETURN d')
nodes_count = len(result['result'])
print(f'ArangoDB - canonical_nodes: {nodes_count}')

# Подсчёт рёбер
result = query_aql('FOR e IN project_relations RETURN e')
edges_count = len(result['result'])
print(f'ArangoDB - project_relations: {edges_count}')

# Примеры узлов
result = query_aql('FOR d IN canonical_nodes LIMIT 5 RETURN {key: d._key, name: d.name}')
print('\nПримеры узлов:')
for node in result['result']:
    print(f"  - {node['key']}: {node.get('name', 'N/A')}")

