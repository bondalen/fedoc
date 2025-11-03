#!/usr/bin/env python3
"""
Скрипт для исправления проблем целостности:
1. Удаляет несуществующие edge_id из edge_projects
2. Мигрирует недостающие рёбра
"""

import sys
import psycopg2

def delete_invalid_edge_ids(conn):
    """Удалить edge_id из таблицы, которых нет в графе"""
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Найти все edge_id из таблицы, которых нет в графе
        cur.execute("""
            DELETE FROM public.edge_projects
            WHERE edge_id IN (
                SELECT ep.edge_id
                FROM public.edge_projects ep
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM cypher('common_project_graph', $$
                        MATCH ()-[e:project_relation]->()
                        RETURN id(e) as edge_id
                    $$) AS (edge_id agtype)
                    WHERE edge_id::text::bigint = ep.edge_id
                )
            )
        """)
        deleted = cur.rowcount
        conn.commit()
        return deleted

def main():
    if len(sys.argv) != 6:
        print("Использование: python fix_integrity_issues.py <host> <port> <database> <user> <password>")
        sys.exit(1)
    
    host, port, database, user, password = sys.argv[1:6]
    
    try:
        conn = psycopg2.connect(host=host, port=int(port), database=database, user=user, password=password)
        conn.autocommit = False
        print("✅ Подключение установлено")
        
        deleted = delete_invalid_edge_ids(conn)
        print(f"✅ Удалено {deleted} записей с несуществующими edge_id")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

