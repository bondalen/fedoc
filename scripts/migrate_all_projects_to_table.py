#!/usr/bin/env python3
"""
Скрипт миграции всех проектов из e.projects в edge_projects
Идемпотентный: пропускает уже существующие записи
"""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Any, Set


def get_all_edges_from_graph(conn):
    """Получить все рёбра из графа с их проектами через Cypher"""
    edges = []
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Получить все рёбра из графа через Cypher
        query = """
        SELECT 
            edge_id::text as edge_id_str,
            projects::text as projects_str
        FROM cypher('common_project_graph', $$
            MATCH ()-[e:project_relation]->()
            RETURN id(e) as edge_id, e.projects as projects
        $$) AS (edge_id agtype, projects agtype)
        WHERE projects IS NOT NULL
        """
        
        cur.execute(query)
        for row in cur.fetchall():
            edge_id_str = str(row['edge_id_str']).strip('"')
            try:
                edge_id = int(edge_id_str)
            except:
                continue
            
            projects_agtype = row.get('projects_str')
            if not projects_agtype:
                continue
            
            # Извлечь projects из agtype строки
            projects = []
            try:
                # agtype может быть в формате ["fedoc","fepro"] или "["fedoc","fepro"]"
                projects_str = str(projects_agtype).strip()
                
                # Попробовать распарсить как JSON
                if projects_str.startswith('['):
                    projects_list = json.loads(projects_str)
                    if isinstance(projects_list, list):
                        projects = [p for p in projects_list if isinstance(p, str)]
                elif projects_str.startswith('"['):
                    # Строка с JSON массивом внутри
                    projects_str_unquoted = projects_str.strip('"')
                    projects_list = json.loads(projects_str_unquoted)
                    if isinstance(projects_list, list):
                        projects = [p for p in projects_list if isinstance(p, str)]
                else:
                    # Попробовать извлечь через регулярное выражение
                    import re
                    matches = re.findall(r'"([^"]+)"', projects_str)
                    projects = matches
            except Exception as e:
                # Если не удалось распарсить, попробовать извлечь через регулярку
                try:
                    import re
                    matches = re.findall(r'"([^"]+)"', str(projects_agtype))
                    projects = matches
                except:
                    print(f"Предупреждение: не удалось распарсить projects для ребра {edge_id}: {projects_agtype}")
            
            if projects:
                edges.append({
                    'edge_id': edge_id,
                    'projects': projects
                })
    
    return edges


def get_existing_edge_projects(conn) -> Set[int]:
    """Получить множество edge_id, которые уже есть в edge_projects"""
    existing = set()
    
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT edge_id FROM public.edge_projects")
        for row in cur.fetchall():
            existing.add(row[0])
    
    return existing


def migrate_projects_to_table(conn, edge_id: int, project_keys: List[str], created_by: str = 'migration_script'):
    """Добавить проекты ребра в edge_projects"""
    migrated_count = 0
    errors = []
    
    with conn.cursor() as cur:
        for project_key in project_keys:
            try:
                # Использовать функцию add_project_to_edge
                cur.execute("""
                    SELECT ag_catalog.add_project_to_edge(
                        %s, %s, 'participant', 1.0, %s, 
                        jsonb_build_object('migrated_from', 'properties.projects', 'migration_date', NOW())
                    )
                """, (edge_id, project_key, created_by))
                
                # Проверить, была ли добавлена новая запись
                if cur.rowcount > 0 or cur.fetchone()[0]:
                    migrated_count += 1
                    
            except psycopg2.errors.UniqueViolation:
                # Уже существует - пропускаем (идемпотентность)
                pass
            except psycopg2.errors.RaiseException as e:
                # Проект не найден
                error_msg = str(e)
                if 'not found' in error_msg.lower():
                    errors.append(f"Проект '{project_key}' не найден для ребра {edge_id}")
                else:
                    errors.append(f"Ошибка для проекта '{project_key}' в ребре {edge_id}: {error_msg}")
            except Exception as e:
                errors.append(f"Неожиданная ошибка для проекта '{project_key}' в ребре {edge_id}: {e}")
    
    return migrated_count, errors


def verify_migration(conn) -> Dict[str, Any]:
    """Проверить результат миграции"""
    stats = {}
    
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")
        
        # Общее количество рёбер с проектами в графе через Cypher
        cur.execute("""
            SELECT COUNT(*) 
            FROM cypher('common_project_graph', $$
                MATCH ()-[e:project_relation]->()
                WHERE e.projects IS NOT NULL
                RETURN id(e) as edge_id
            $$) AS (edge_id agtype)
        """)
        stats['edges_in_graph_with_projects'] = cur.fetchone()[0]
        
        # Количество рёбер в edge_projects
        cur.execute("SELECT COUNT(DISTINCT edge_id) FROM public.edge_projects")
        stats['edges_in_table'] = cur.fetchone()[0]
        
        # Общее количество связей проект-ребро
        cur.execute("SELECT COUNT(*) FROM public.edge_projects")
        stats['total_project_edge_relations'] = cur.fetchone()[0]
        
        # Количество уникальных проектов в связях
        cur.execute("SELECT COUNT(DISTINCT project_id) FROM public.edge_projects")
        stats['unique_projects_in_relations'] = cur.fetchone()[0]
        
        # Рёбра, которые есть в графе, но нет в таблице
        # Получаем все edge_id из графа с projects и проверяем их наличие в таблице
        cur.execute("""
            SELECT COUNT(*) 
            FROM (
                SELECT edge_id::text as edge_id_str
                FROM cypher('common_project_graph', $$
                    MATCH ()-[e:project_relation]->()
                    WHERE e.projects IS NOT NULL
                    RETURN id(e) as edge_id
                $$) AS (edge_id agtype)
            ) as graph_edges
            WHERE edge_id_str::bigint NOT IN (SELECT DISTINCT edge_id FROM public.edge_projects)
        """)
        stats['missing_in_table'] = cur.fetchone()[0]
    
    return stats


def main():
    """Основная функция миграции"""
    if len(sys.argv) != 6:
        print("Использование: python migrate_all_projects_to_table.py <host> <port> <database> <user> <password>")
        sys.exit(1)
    
    host, port, database, user, password = sys.argv[1:6]
    
    print("=" * 60)
    print("Миграция проектов из e.projects в edge_projects")
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
        conn.autocommit = False
        print(f"✅ Подключение к базе данных {database} установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
    
    try:
        # Шаг 1: Получить все рёбра с проектами
        print("\n📊 Шаг 1: Получение всех рёбер из графа...")
        edges = get_all_edges_from_graph(conn)
        print(f"   Найдено {len(edges)} рёбер с проектами")
        
        # Шаг 2: Получить уже существующие записи
        print("\n📊 Шаг 2: Проверка существующих записей в edge_projects...")
        existing_edges = get_existing_edge_projects(conn)
        print(f"   Найдено {len(existing_edges)} рёбер уже в таблице")
        
        # Шаг 3: Миграция
        print("\n🚀 Шаг 3: Миграция данных...")
        total_migrated = 0
        total_skipped = 0
        all_errors = []
        
        for i, edge in enumerate(edges, 1):
            edge_id = edge['edge_id']
            project_keys = edge['projects']
            
            if edge_id in existing_edges:
                # Проверить, есть ли все проекты
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.key 
                        FROM public.edge_projects ep
                        JOIN public.projects p ON ep.project_id = p.id
                        WHERE ep.edge_id = %s
                    """, (edge_id,))
                    existing_projects = {row[0] for row in cur.fetchall()}
                    
                    missing_projects = set(project_keys) - existing_projects
                    if missing_projects:
                        # Добавить недостающие проекты
                        migrated, errors = migrate_projects_to_table(conn, edge_id, list(missing_projects))
                        total_migrated += migrated
                        all_errors.extend(errors)
                    else:
                        total_skipped += 1
            else:
                # Новая запись - мигрировать все проекты
                migrated, errors = migrate_projects_to_table(conn, edge_id, project_keys)
                total_migrated += migrated
                all_errors.extend(errors)
                if migrated == 0:
                    total_skipped += 1
            
            if i % 10 == 0:
                print(f"   Обработано {i}/{len(edges)} рёбер...")
                conn.commit()  # Промежуточные коммиты
        
        # Финальный коммит
        conn.commit()
        
        print(f"\n✅ Миграция завершена:")
        print(f"   Мигрировано проектов: {total_migrated}")
        print(f"   Пропущено (уже есть): {total_skipped}")
        if all_errors:
            print(f"   Ошибок: {len(all_errors)}")
            for error in all_errors[:10]:  # Показать первые 10 ошибок
                print(f"      ⚠️  {error}")
            if len(all_errors) > 10:
                print(f"      ... и ещё {len(all_errors) - 10} ошибок")
        
        # Шаг 4: Проверка результата
        print("\n📊 Шаг 4: Проверка результата миграции...")
        stats = verify_migration(conn)
        print(f"   Рёбер с проектами в графе: {stats['edges_in_graph_with_projects']}")
        print(f"   Рёбер в таблице edge_projects: {stats['edges_in_table']}")
        print(f"   Всего связей проект-ребро: {stats['total_project_edge_relations']}")
        print(f"   Уникальных проектов в связях: {stats['unique_projects_in_relations']}")
        if stats['missing_in_table'] > 0:
            print(f"   ⚠️  Рёбер без проектов в таблице: {stats['missing_in_table']}")
        else:
            print(f"   ✅ Все рёбра успешно мигрированы!")
        
        print("\n" + "=" * 60)
        print("Миграция завершена успешно!")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка во время миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()

