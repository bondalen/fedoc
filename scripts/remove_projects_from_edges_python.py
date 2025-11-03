#!/usr/bin/env python3
"""
Скрипт удаления поля projects из всех рёбер графа через Cypher
"""

import sys
import psycopg2

def remove_projects_from_edges(conn):
    """Удалить поле projects из всех рёбер через Cypher"""
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Получить все edge_id рёбер с projects
        cur.execute("""
            SELECT edge_id::text as edge_id_str
            FROM cypher('common_project_graph', $$
                MATCH ()-[e:project_relation]->()
                WHERE e.projects IS NOT NULL
                RETURN id(e) as edge_id
            $$) AS (edge_id agtype)
        """)
        
        edge_ids = []
        for row in cur.fetchall():
            try:
                edge_id = int(str(row[0]).strip('"'))
                edge_ids.append(edge_id)
            except:
                continue
        
        print(f"   Найдено {len(edge_ids)} рёбер с projects")
        
        # Удалить projects из каждого ребра
        updated_count = 0
        for edge_id in edge_ids:
            try:
                # Удалить поле через Cypher
                cur.execute(f"""
                    SELECT * FROM cypher('common_project_graph', $$
                        MATCH ()-[e]->()
                        WHERE id(e) = {edge_id}
                        REMOVE e.projects
                        RETURN id(e) as edge_id
                    $$) AS (edge_id agtype)
                """)
                result = cur.fetchone()
                if result:
                    updated_count += 1
                    
            except Exception as e:
                print(f"      ⚠️  Ошибка при удалении projects из ребра {edge_id}: {e}")
        
        conn.commit()
        return updated_count

def main():
    if len(sys.argv) != 6:
        print("Использование: python remove_projects_from_edges_python.py <host> <port> <database> <user> <password>")
        sys.exit(1)
    
    host, port, database, user, password = sys.argv[1:6]
    
    print("=" * 60)
    print("Удаление поля projects из рёбер графа")
    print("=" * 60)
    print()
    
    try:
        conn = psycopg2.connect(host=host, port=int(port), database=database, user=user, password=password)
        conn.autocommit = False
        print("✅ Подключение установлено")
        
        print("\n🚀 Удаление projects из рёбер...")
        updated = remove_projects_from_edges(conn)
        print(f"\n✅ Удалено поле projects из {updated} рёбер")
        
        # Финальная проверка
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            cur.execute("""
                SELECT COUNT(*) 
                FROM cypher('common_project_graph', $$
                    MATCH ()-[e:project_relation]->()
                    WHERE e.projects IS NOT NULL
                    RETURN id(e) as edge_id
                $$) AS (edge_id agtype)
            """)
            remaining = cur.fetchone()[0]
            
            if remaining == 0:
                print("✅ Все поля projects успешно удалены!")
            else:
                print(f"⚠️  Осталось {remaining} рёбер с полем projects")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

