#!/usr/bin/env python3
"""
Скрипт тестирования API сервера с PostgreSQL + Apache AGE

Тестирует основные endpoints и операции с графом
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8899"


def test_api():
    """Запустить все тесты"""
    
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ API С POSTGRESQL + AGE")
    print("=" * 60)
    
    # Тест 1: Получение узлов
    print("\n1️⃣ Тест GET /api/nodes")
    response = requests.get(f"{API_URL}/api/nodes")
    if response.status_code == 200:
        nodes = response.json()
        print(f"   ✅ Получено узлов: {len(nodes)}")
        if nodes:
            print(f"   Пример: {nodes[0]}")
    else:
        print(f"   ❌ Ошибка: {response.status_code}")
        print(f"   {response.text}")
    
    # Тест 2: Построение графа
    print("\n2️⃣ Тест GET /api/graph")
    response = requests.get(
        f"{API_URL}/api/graph",
        params={
            'start': 'canonical_nodes/c:backend',
            'depth': 3,
            'theme': 'dark'
        }
    )
    if response.status_code == 200:
        graph = response.json()
        print(f"   ✅ Граф построен")
        print(f"   Узлов: {len(graph.get('nodes', []))}")
        print(f"   Рёбер: {len(graph.get('edges', []))}")
    else:
        print(f"   ❌ Ошибка: {response.status_code}")
        print(f"   {response.text}")
    
    # Тест 3: Создание ребра
    print("\n3️⃣ Тест POST /api/edges (создание)")
    
    # Сначала получим два узла для создания связи
    response = requests.get(f"{API_URL}/api/nodes", params={'limit': 2})
    if response.status_code == 200 and len(response.json()) >= 2:
        nodes = response.json()
        from_node = nodes[0]['_id']
        to_node = nodes[1]['_id']
        
        edge_data = {
            '_from': from_node,
            '_to': to_node,
            'relationType': 'test',
            'projects': ['test']
        }
        
        response = requests.post(
            f"{API_URL}/api/edges",
            json=edge_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"   ✅ Ребро создано: {result.get('edge')}")
            else:
                print(f"   ⚠️  Валидация: {result.get('error')}")
        else:
            print(f"   ❌ Ошибка: {response.status_code}")
            print(f"   {response.text}")
    else:
        print("   ⚠️  Недостаточно узлов для теста")
    
    # Тест 4: Проверка уникальности
    print("\n4️⃣ Тест POST /api/edges/check (уникальность)")
    response = requests.post(
        f"{API_URL}/api/edges/check",
        json={
            '_from': '844424930131969',
            '_to': '844424930131970',
        }
    )
    if response.status_code == 200:
        result = response.json()
        is_unique = result.get('is_unique')
        print(f"   {'✅' if is_unique else '⚠️ '} Уникальна: {is_unique}")
        if not is_unique:
            print(f"   Ошибка: {result.get('error')}")
    else:
        print(f"   ❌ Ошибка: {response.status_code}")
    
    # Тест 5: Детали объекта
    print("\n5️⃣ Тест GET /api/object_details")
    response = requests.get(
        f"{API_URL}/api/object_details",
        params={'id': '844424930131969'}
    )
    if response.status_code == 200:
        obj = response.json()
        print(f"   ✅ Объект получен: {obj}")
    else:
        print(f"   ❌ Ошибка: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_api()
    except requests.ConnectionError:
        print("\n❌ Не удалось подключиться к API серверу")
        print(f"   URL: {API_URL}")
        print("   Убедитесь что сервер запущен:")
        print("   python3 api_server_age.py --db-password <password>")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

