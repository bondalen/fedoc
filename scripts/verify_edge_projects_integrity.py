#!/usr/bin/env python3
"""
Скрипт проверки целостности данных в edge_projects
Проверяет:
1. Все рёбра с e.projects должны быть в edge_projects
2. Все записи edge_projects должны ссылаться на существующие рёбра
3. Нет дубликатов в edge_projects
4. Все project_id существуют в projects
5. Нет рёбер с проектами в графе, которых нет в таблице
"""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import Dict, List, Set


def get_edges_with_projects_from_graph(conn) -> Set[int]:
    """Получить множество edge_id рёбер, которые имеют projects в графе"""
    edge_ids = set()
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        query = """
        SELECT edge_id::text as edge_id_str
        FROM cypher('common_project_graph', $$
            MATCH ()-[e:project_relation]->()
            WHERE e.projects IS NOT NULL
            RETURN id(e) as edge_id
        $$) AS (edge_id agtype)
        """
        
        cur.execute(query)
        for row in cur.fetchall():
            try:
                edge_id = int(str(row['edge_id_str']).strip('"'))
                edge_ids.add(edge_id)
            except:
                continue
    
    return edge_ids


def get_edges_from_table(conn) -> Set[int]:
    """Получить множество edge_id из edge_projects"""
    edge_ids = set()
    
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT edge_id FROM public.edge_projects")
        for row in cur.fetchall():
            edge_ids.add(row[0])
    
    return edge_ids


def get_all_edge_ids_from_graph(conn) -> Set[int]:
    """Получить все edge_id из графа"""
    edge_ids = set()
    
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        cur.execute("""
            SELECT edge_id::text as edge_id_str
            FROM cypher('common_project_graph', $$
                MATCH ()-[e:project_relation]->()
                RETURN id(e) as edge_id
            $$) AS (edge_id agtype)
        """)
        for row in cur.fetchall():
            try:
                edge_id = int(str(row[0]).strip('"'))
                edge_ids.add(edge_id)
            except:
                continue
    
    return edge_ids


def check_duplicates_in_table(conn) -> List[Dict]:
    """Проверить дубликаты в edge_projects"""
    duplicates = []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT edge_id, project_id, COUNT(*) as count
            FROM public.edge_projects
            GROUP BY edge_id, project_id
            HAVING COUNT(*) > 1
        """)
        
        for row in cur.fetchall():
            duplicates.append({
                'edge_id': row['edge_id'],
                'project_id': row['project_id'],
                'count': row['count']
            })
    
    return duplicates


def check_invalid_project_ids(conn) -> List[Dict]:
    """Проверить, что все project_id существуют в таблице projects"""
    invalid = []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT ep.edge_id, ep.project_id
            FROM public.edge_projects ep
            LEFT JOIN public.projects p ON ep.project_id = p.id
            WHERE p.id IS NULL
        """)
        
        for row in cur.fetchall():
            invalid.append({
                'edge_id': row['edge_id'],
                'project_id': row['project_id']
            })
    
    return invalid


def check_invalid_edge_ids(conn, valid_edge_ids: Set[int]) -> List[int]:
    """Проверить, что все edge_id из таблицы существуют в графе"""
    invalid = []
    
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT edge_id FROM public.edge_projects")
        for row in cur.fetchall():
            edge_id = row[0]
            if edge_id not in valid_edge_ids:
                invalid.append(edge_id)
    
    return invalid


def main():
    """Основная функция проверки"""
    if len(sys.argv) != 6:
        print("Использование: python verify_edge_projects_integrity.py <host> <port> <database> <user> <password>")
        sys.exit(1)
    
    host, port, database, user, password = sys.argv[1:6]
    
    print("=" * 60)
    print("Проверка целостности данных edge_projects")
    print("=" * 60)
    print()
    
    # Подключение к базе данных
    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password
        )
        print(f"✅ Подключение к базе данных {database} установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
    
    try:
        all_ok = True
        
        # Проверка 1: Рёбра с projects в графе должны быть в таблице
        print("\n📊 Проверка 1: Рёбра с e.projects в графе...")
        edges_with_projects_in_graph = get_edges_with_projects_from_graph(conn)
        edges_in_table = get_edges_from_table(conn)
        
        missing_in_table = edges_with_projects_in_graph - edges_in_table
        
        print(f"   Рёбер с projects в графе: {len(edges_with_projects_in_graph)}")
        print(f"   Рёбер в таблице edge_projects: {len(edges_in_table)}")
        
        if missing_in_table:
            print(f"   ⚠️  Рёбер без проектов в таблице: {len(missing_in_table)}")
            if len(missing_in_table) <= 10:
                for edge_id in sorted(missing_in_table):
                    print(f"      - Edge ID: {edge_id}")
            else:
                for edge_id in sorted(list(missing_in_table))[:10]:
                    print(f"      - Edge ID: {edge_id}")
                print(f"      ... и ещё {len(missing_in_table) - 10} рёбер")
            all_ok = False
        else:
            print(f"   ✅ Все рёбра с projects есть в таблице")
        
        # Проверка 2: Дубликаты в таблице
        print("\n📊 Проверка 2: Дубликаты в edge_projects...")
        duplicates = check_duplicates_in_table(conn)
        
        if duplicates:
            print(f"   ⚠️  Найдено {len(duplicates)} дубликатов:")
            for dup in duplicates[:10]:
                print(f"      - Edge {dup['edge_id']} + Project {dup['project_id']}: {dup['count']} записей")
            if len(duplicates) > 10:
                print(f"      ... и ещё {len(duplicates) - 10} дубликатов")
            all_ok = False
        else:
            print(f"   ✅ Дубликатов не найдено")
        
        # Проверка 3: Несуществующие project_id
        print("\n📊 Проверка 3: Валидность project_id...")
        invalid_projects = check_invalid_project_ids(conn)
        
        if invalid_projects:
            print(f"   ⚠️  Найдено {len(invalid_projects)} несуществующих project_id:")
            for inv in invalid_projects[:10]:
                print(f"      - Edge {inv['edge_id']} ссылается на несуществующий project_id {inv['project_id']}")
            if len(invalid_projects) > 10:
                print(f"      ... и ещё {len(invalid_projects) - 10} ошибок")
            all_ok = False
        else:
            print(f"   ✅ Все project_id валидны")
        
        # Проверка 4: Несуществующие edge_id
        print("\n📊 Проверка 4: Валидность edge_id...")
        all_edge_ids = get_all_edge_ids_from_graph(conn)
        invalid_edges = check_invalid_edge_ids(conn, all_edge_ids)
        
        if invalid_edges:
            print(f"   ⚠️  Найдено {len(invalid_edges)} несуществующих edge_id:")
            for edge_id in invalid_edges[:10]:
                print(f"      - Edge ID {edge_id} не существует в графе")
            if len(invalid_edges) > 10:
                print(f"      ... и ещё {len(invalid_edges) - 10} ошибок")
            all_ok = False
        else:
            print(f"   ✅ Все edge_id валидны")
        
        # Итоговый результат
        print("\n" + "=" * 60)
        if all_ok:
            print("✅ Все проверки пройдены успешно!")
        else:
            print("⚠️  Обнаружены проблемы с целостностью данных")
            print("   Рекомендуется запустить migrate_all_projects_to_table.py")
        print("=" * 60)
        
        return 0 if all_ok else 1
        
    except Exception as e:
        print(f"\n❌ Ошибка во время проверки: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())

