#!/usr/bin/env python3
"""
Скрипт миграции данных из ArangoDB в PostgreSQL + Apache AGE

Миграция коллекций:
- canonical_nodes → canonical_node (vertices)
- project_relations → project_relation (edges)

Автор: Александр
Дата: 18 октября 2025
"""

import sys
import json
import argparse
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import Json
from arango import ArangoClient
from arango.database import StandardDatabase


def dict_to_cypher_map(d: Dict[str, Any]) -> str:
    """
    Конвертировать Python dict в Cypher map формат
    
    Python: {'name': 'Backend', 'count': 42, 'active': True}
    Cypher: {name: 'Backend', count: 42, active: true}
    
    Args:
        d: Python словарь
    
    Returns:
        Строка в формате Cypher map
    """
    def format_value(v):
        if v is None:
            return 'null'
        elif isinstance(v, bool):
            return 'true' if v else 'false'
        elif isinstance(v, (int, float)):
            return str(v)
        elif isinstance(v, str):
            # Экранировать одинарные кавычки
            escaped = v.replace("'", "\\'")
            return f"'{escaped}'"
        elif isinstance(v, list):
            # Массив: [1, 2, 3] или ['a', 'b']
            items = [format_value(item) for item in v]
            return '[' + ', '.join(items) + ']'
        elif isinstance(v, dict):
            # Вложенный объект
            return dict_to_cypher_map(v)
        else:
            # Fallback - конвертировать в строку
            escaped = str(v).replace("'", "\\'")
            return f"'{escaped}'"
    
    if not d:
        return '{}'
    
    items = []
    for k, v in d.items():
        items.append(f"{k}: {format_value(v)}")
    
    return '{' + ', '.join(items) + '}'


class ArangoToAGEMigrator:
    """Класс для миграции данных из ArangoDB в Apache AGE"""
    
    def __init__(
        self,
        arango_host: str,
        arango_db: str,
        arango_user: str,
        arango_password: str,
        pg_host: str,
        pg_port: int,
        pg_db: str,
        pg_user: str,
        pg_password: str,
        graph_name: str = 'common_project_graph'
    ):
        """Инициализация миграции"""
        self.graph_name = graph_name
        
        # Подключение к ArangoDB
        print(f"📡 Подключение к ArangoDB ({arango_host})...")
        arango_client = ArangoClient(hosts=arango_host)
        self.arango_db: StandardDatabase = arango_client.db(
            arango_db,
            username=arango_user,
            password=arango_password
        )
        print("✓ Подключено к ArangoDB")
        
        # Подключение к PostgreSQL
        print(f"📡 Подключение к PostgreSQL ({pg_host}:{pg_port})...")
        self.pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_db,
            user=pg_user,
            password=pg_password
        )
        self.pg_conn.autocommit = False
        print("✓ Подключено к PostgreSQL")
        
        # Загрузить расширение AGE и настроить search_path
        with self.pg_conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, \"$user\", public;")
        
        # Маппинг ID ArangoDB → ID AGE
        self.id_mapping: Dict[str, int] = {}
    
    def migrate_vertices(self, collection_name: str, vertex_label: str) -> int:
        """
        Миграция вершин из ArangoDB коллекции в AGE
        
        Args:
            collection_name: Имя коллекции в ArangoDB (например, 'canonical_nodes')
            vertex_label: Метка вершин в AGE (например, 'canonical_node')
        
        Returns:
            Количество мигрированных вершин
        """
        print(f"\n📦 Миграция вершин: {collection_name} → {vertex_label}")
        
        # Получить все документы из ArangoDB
        query = f"FOR d IN {collection_name} RETURN d"
        cursor = self.arango_db.aql.execute(query)
        documents = list(cursor)
        
        print(f"   Найдено документов: {len(documents)}")
        
        migrated = 0
        with self.pg_conn.cursor() as cur:
            # Загрузить AGE для этой сессии
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            for doc in documents:
                arango_id = doc['_id']
                arango_key = doc['_key']
                
                # Подготовить properties (все поля кроме системных)
                properties = {
                    k: v for k, v in doc.items() 
                    if not k.startswith('_')
                }
                
                # Добавить оригинальный _key для обратной совместимости
                properties['arango_key'] = arango_key
                
                # Конвертировать properties в Cypher map формат
                props_cypher = dict_to_cypher_map(properties)
                
                # Создать вершину в AGE через Cypher
                cypher_query = f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    CREATE (n:{vertex_label} {props_cypher})
                    RETURN id(n) as vertex_id
                $$) as (vertex_id agtype)
                """
                
                cur.execute(cypher_query)
                
                result = cur.fetchone()
                if result and result[0]:
                    age_id = int(str(result[0]).strip('"'))
                    
                    # Сохранить маппинг ID
                    self.id_mapping[arango_id] = age_id
                    
                    migrated += 1
                    if migrated % 10 == 0:
                        print(f"   Прогресс: {migrated}/{len(documents)}")
                else:
                    print(f"⚠️  Не удалось создать вершину для {arango_key}")
        
        self.pg_conn.commit()
        print(f"✓ Мигрировано вершин: {migrated}")
        
        return migrated
    
    def migrate_edges(
        self, 
        collection_name: str, 
        edge_label: str,
        use_validation: bool = True
    ) -> int:
        """
        Миграция рёбер из ArangoDB коллекции в AGE
        
        Args:
            collection_name: Имя edge-коллекции в ArangoDB
            edge_label: Метка рёбер в AGE
            use_validation: Использовать функцию create_edge_safe() для валидации
        
        Returns:
            Количество мигрированных рёбер
        """
        print(f"\n🔗 Миграция рёбер: {collection_name} → {edge_label}")
        
        # Получить все рёбра из ArangoDB
        query = f"FOR e IN {collection_name} RETURN e"
        cursor = self.arango_db.aql.execute(query)
        edges = list(cursor)
        
        print(f"   Найдено рёбер: {len(edges)}")
        
        migrated = 0
        skipped = 0
        
        with self.pg_conn.cursor() as cur:
            # Загрузить AGE для этой сессии
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            for edge in edges:
                from_arango = edge['_from']
                to_arango = edge['_to']
                
                # Получить ID вершин в AGE
                if from_arango not in self.id_mapping:
                    print(f"⚠️  Пропущено ребро: вершина {from_arango} не найдена")
                    skipped += 1
                    continue
                
                if to_arango not in self.id_mapping:
                    print(f"⚠️  Пропущено ребро: вершина {to_arango} не найдена")
                    skipped += 1
                    continue
                
                from_age = self.id_mapping[from_arango]
                to_age = self.id_mapping[to_arango]
                
                # Подготовить properties
                properties = {
                    k: v for k, v in edge.items() 
                    if not k.startswith('_')
                }
                
                if use_validation:
                    # Использовать функцию валидации
                    cur.execute(
                        """
                        SELECT * FROM create_edge_safe(
                            %s::text,
                            %s::bigint,
                            %s::bigint,
                            %s::text,
                            %s::jsonb
                        )
                        """,
                        [
                            self.graph_name,
                            from_age,
                            to_age,
                            edge_label,
                            Json(properties)
                        ]
                    )
                    
                    result = cur.fetchone()
                    success = result[0]
                    
                    if not success:
                        error_msg = result[2]
                        print(f"⚠️  Ошибка валидации: {error_msg}")
                        skipped += 1
                        continue
                else:
                    # Прямое создание через Cypher
                    props_cypher = dict_to_cypher_map(properties)
                    
                    cypher_query = f"""
                    SELECT * FROM cypher('{self.graph_name}', $$
                        MATCH (a), (b)
                        WHERE id(a) = {from_age} AND id(b) = {to_age}
                        CREATE (a)-[e:{edge_label} {props_cypher}]->(b)
                        RETURN id(e) as edge_id
                    $$) as (edge_id agtype)
                    """
                    
                    cur.execute(cypher_query)
                
                migrated += 1
                if migrated % 10 == 0:
                    print(f"   Прогресс: {migrated}/{len(edges)}")
        
        self.pg_conn.commit()
        print(f"✓ Мигрировано рёбер: {migrated}")
        if skipped > 0:
            print(f"⚠️  Пропущено: {skipped}")
        
        return migrated
    
    def verify_migration(self) -> Dict[str, Any]:
        """Проверить результаты миграции"""
        print("\n🔍 Проверка миграции...")
        
        stats = {}
        
        with self.pg_conn.cursor() as cur:
            # Загрузить AGE
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, public;")
            
            # Подсчёт вершин
            cur.execute(f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    MATCH (n)
                    RETURN count(n) as cnt
                $$) as (cnt agtype)
            """)
            result = cur.fetchone()
            stats['vertices'] = int(str(result[0]).strip('"'))
            
            # Подсчёт рёбер
            cur.execute(f"""
                SELECT * FROM cypher('{self.graph_name}', $$
                    MATCH ()-[e]->()
                    RETURN count(e) as cnt
                $$) as (cnt agtype)
            """)
            result = cur.fetchone()
            stats['edges'] = int(str(result[0]).strip('"'))
        
        print(f"   Вершин в AGE: {stats['vertices']}")
        print(f"   Рёбер в AGE: {stats['edges']}")
        
        return stats
    
    def export_id_mapping(self, filename: str):
        """Экспортировать маппинг ID в JSON"""
        print(f"\n💾 Экспорт маппинга ID в {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.id_mapping, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Экспортировано {len(self.id_mapping)} маппингов")
    
    def close(self):
        """Закрыть подключения"""
        if self.pg_conn:
            self.pg_conn.close()
        print("\n✓ Подключения закрыты")


def main():
    parser = argparse.ArgumentParser(
        description='Миграция данных из ArangoDB в PostgreSQL + Apache AGE'
    )
    
    # ArangoDB параметры
    parser.add_argument('--arango-host', default='http://localhost:8529')
    parser.add_argument('--arango-db', default='fedoc')
    parser.add_argument('--arango-user', default='root')
    parser.add_argument('--arango-password', required=True)
    
    # PostgreSQL параметры
    parser.add_argument('--pg-host', default='localhost')
    parser.add_argument('--pg-port', type=int, default=5432)
    parser.add_argument('--pg-db', default='fedoc')
    parser.add_argument('--pg-user', default='postgres')
    parser.add_argument('--pg-password', required=True)
    
    # Опции миграции
    parser.add_argument('--graph-name', default='common_project_graph')
    parser.add_argument('--no-validation', action='store_true',
                       help='Не использовать функции валидации при миграции рёбер')
    parser.add_argument('--export-mapping', 
                       help='Экспортировать маппинг ID в JSON файл')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔄 МИГРАЦИЯ ARANGO → POSTGRESQL + AGE")
    print("=" * 60)
    
    try:
        # Создать мигратор
        migrator = ArangoToAGEMigrator(
            arango_host=args.arango_host,
            arango_db=args.arango_db,
            arango_user=args.arango_user,
            arango_password=args.arango_password,
            pg_host=args.pg_host,
            pg_port=args.pg_port,
            pg_db=args.pg_db,
            pg_user=args.pg_user,
            pg_password=args.pg_password,
            graph_name=args.graph_name
        )
        
        # Миграция вершин
        migrator.migrate_vertices('canonical_nodes', 'canonical_node')
        
        # Миграция рёбер
        migrator.migrate_edges(
            'project_relations', 
            'project_relation',
            use_validation=not args.no_validation
        )
        
        # Проверка
        stats = migrator.verify_migration()
        
        # Экспорт маппинга
        if args.export_mapping:
            migrator.export_id_mapping(args.export_mapping)
        
        migrator.close()
        
        print("\n" + "=" * 60)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print(f"Мигрировано вершин: {stats['vertices']}")
        print(f"Мигрировано рёбер: {stats['edges']}")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ОШИБКА МИГРАЦИИ: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

