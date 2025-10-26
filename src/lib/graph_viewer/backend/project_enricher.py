#!/usr/bin/env python3
"""
Модуль для обогащения данных проектов в рёбрах графа
Преобразует простые массивы проектов в структурированные объекты с полной информацией
"""

from typing import List, Dict, Any, Optional
import psycopg2
import sys
from psycopg2.extras import RealDictCursor


def enrich_projects_data(db_conn, projects: List[str]) -> List[Dict[str, Any]]:
    """
    Обогатить данные проектов полной информацией из базы данных
    
    Args:
        db_conn: Соединение с PostgreSQL
        projects: Список ключей проектов (например, ["fedoc", "fepro"])
    
    Returns:
        List[Dict]: Список объектов с полной информацией о проектах
    """
    if not projects:
        return []
    
    enriched_projects = []
    
    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Получить информацию о каждом проекте
            for project_key in projects:
                cur.execute("""
                    SELECT key, name, description, data, created_at, updated_at 
                    FROM public.projects 
                    WHERE key = %s
                """, (project_key,))
                
                row = cur.fetchone()
                if row:
                    # Создать структурированный объект проекта
                    project_info = {
                        "id": row['key'],
                        "name": row['name'],
                        "description": row['description'],
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "data": row['data'] if row['data'] else {}
                    }
                    enriched_projects.append(project_info)
                else:
                    # Если проект не найден, добавить базовую информацию
                    enriched_projects.append({
                        "id": project_key,
                        "name": project_key,
                        "description": f"Проект {project_key} (не найден в базе)",
                        "created_at": None,
                        "updated_at": None,
                        "data": {}
                    })
    
    except Exception as e:
        print(f"Ошибка обогащения данных проектов: {e}", file=sys.stderr)
        # В случае ошибки вернуть базовую структуру
        return [{"id": p, "name": p, "description": f"Проект {p}"} for p in projects]
    
    return enriched_projects


def enrich_edge_properties(db_conn, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обогатить свойства ребра, заменив простые массивы проектов на структурированные данные
    
    Args:
        db_conn: Соединение с PostgreSQL
        properties: Свойства ребра
    
    Returns:
        Dict: Обогащённые свойства ребра
    """
    enriched_properties = properties.copy()
    
    # Если есть поле projects с массивом строк
    if 'projects' in enriched_properties and isinstance(enriched_properties['projects'], list):
        projects = enriched_properties['projects']
        if projects and isinstance(projects[0], str):
            # Обогатить данные проектов
            enriched_projects = enrich_projects_data(db_conn, projects)
            enriched_properties['projects'] = enriched_projects
    
    return enriched_properties


def enrich_object_properties(db_conn, obj_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обогатить свойства объекта (узла или ребра) структурированными данными проектов
    
    Args:
        db_conn: Соединение с PostgreSQL
        obj_data: Данные объекта
    
    Returns:
        Dict: Обогащённые данные объекта
    """
    enriched_data = obj_data.copy()
    
    # Обработать properties если они есть
    if 'properties' in enriched_data and isinstance(enriched_data['properties'], dict):
        enriched_data['properties'] = enrich_edge_properties(db_conn, enriched_data['properties'])
    
    return enriched_data
