#!/usr/bin/env python3
"""
Скрипт для выполнения миграций нормализованной структуры проектов
"""

import sys
import psycopg2
from pathlib import Path

def run_migration(db_conn, migration_file):
    """Выполнить миграцию из файла"""
    print(f"Выполняем миграцию: {migration_file}")
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with db_conn.cursor() as cur:
            cur.execute(migration_sql)
            db_conn.commit()
        
        print(f"✅ Миграция {migration_file} выполнена успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в миграции {migration_file}: {e}")
        db_conn.rollback()
        return False

def main():
    """Основная функция выполнения миграций"""
    if len(sys.argv) != 6:
        print("Использование: python run_migrations.py <host> <port> <database> <user> <password>")
        sys.exit(1)
    
    host, port, database, user, password = sys.argv[1:6]
    
    # Подключение к базе данных
    try:
        db_conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print(f"✅ Подключение к базе данных {database} установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
    
    # Список миграций в порядке выполнения
    migrations_dir = Path(__file__).parent / "migrations"
    migrations = [
        "001_create_normalized_projects.sql",
        "002_create_project_functions.sql", 
        "003_migrate_existing_data.sql"
    ]
    
    print("🚀 Начинаем выполнение миграций...")
    
    success_count = 0
    for migration in migrations:
        migration_file = migrations_dir / migration
        if migration_file.exists():
            if run_migration(db_conn, migration_file):
                success_count += 1
            else:
                print(f"❌ Миграция {migration} не выполнена. Останавливаем процесс.")
                break
        else:
            print(f"⚠️ Файл миграции {migration} не найден")
    
    print(f"\n📊 Результат: {success_count}/{len(migrations)} миграций выполнено успешно")
    
    if success_count == len(migrations):
        print("🎉 Все миграции выполнены успешно!")
    else:
        print("⚠️ Некоторые миграции не выполнены. Проверьте ошибки выше.")
    
    db_conn.close()

if __name__ == "__main__":
    main()
