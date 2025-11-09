"""Seed utility for multigraph demo data."""
from __future__ import annotations

import argparse
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List

from ..config.settings import Settings
from ..db.session import SessionManager
from ..db.repositories.blocks import BlocksRepository
from ..db.repositories.designs import DesignsRepository
from ..db.repositories.projects import ProjectsRepository


def _ensure_graph_empty(session_manager: SessionManager, graph_name: str) -> None:
    with session_manager.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM ag_catalog.cypher('{graph_name}', $$MATCH (n) DETACH DELETE n$$) "
            "AS (result agtype)"
        )


def _clear_relational_links(session_manager: SessionManager) -> None:
    with session_manager.cursor() as cursor:
        cursor.execute("DELETE FROM mg.design_to_block")
        cursor.execute("DELETE FROM mg.design_edge_to_project")
        cursor.execute("DELETE FROM mg.projects")


def seed_blocks(repository: BlocksRepository) -> Dict[str, Dict[str, str]]:
    blocks_config = [
        {
            "name": "Core Platform",
            "description": "Базовый слой платформы multigraph.",
            "type": "system",
            "metadata": {"owner": "core-team", "tier": "core"},
        },
        {
            "name": "Authentication Module",
            "description": "Поток авторизации и управления сессиями.",
            "type": "service",
            "parent": "Core Platform",
            "relation_type": "contains",
            "metadata": {"owner": "auth-team"},
        },
        {
            "name": "UI Library",
            "description": "Общие компоненты интерфейса и визуальные паттерны.",
            "type": "library",
            "parent": "Core Platform",
            "relation_type": "contains",
            "metadata": {"owner": "frontend-team"},
        },
        {
            "name": "Data Warehouse",
            "description": "Хранилище данных для аналитических сценариев.",
            "type": "service",
            "parent": "Core Platform",
            "relation_type": "depends_on",
            "metadata": {"owner": "data-team"},
        },
        {
            "name": "Analytics Engine",
            "description": "Поток обработки данных и расчёта метрик.",
            "type": "service",
            "parent": "Data Warehouse",
            "relation_type": "contains",
            "metadata": {"owner": "analytics-team"},
        },
        {
            "name": "Reporting Service",
            "description": "Сервис формирования отчётов и дашбордов.",
            "type": "service",
            "parent": "Analytics Engine",
            "relation_type": "extends",
            "metadata": {"owner": "business-intel"},
        },
        {
            "name": "Notification Service",
            "description": "Сервис отправки уведомлений и событий.",
            "type": "service",
            "parent": "Core Platform",
            "relation_type": "contains",
            "metadata": {"owner": "operations"},
        },
    ]

    created: Dict[str, Dict[str, str]] = {}
    for config in blocks_config:
        parent_name = config.get("parent")
        relation_type = config.get("relation_type", "contains")
        payload = {
            key: value
            for key, value in config.items()
            if key not in {"parent", "relation_type"}
        }
        if parent_name:
            payload["relation_type"] = relation_type
        parent_id = created[parent_name]["id"] if parent_name else None
        block = repository.create(payload, parent_id=parent_id)
        created[config["name"]] = block
    return created


def seed_designs(repository: DesignsRepository, blocks: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    now = datetime.now(tz=timezone.utc)
    designs_config = [
        {
            "name": "Project Atlas",
            "description": "Производственный дизайн, используемый в клиентских проектах.",
            "status": "active",
            "metadata": {"owner": "solutions", "release": "2025-Q1"},
            "block": "Core Platform",
            "created_at": now,
        },
        {
            "name": "Prototype Nova",
            "description": "Экспериментальный дизайн для исследовательских задач.",
            "status": "draft",
            "metadata": {"owner": "research", "risk": "high"},
            "block": "Authentication Module",
            "created_at": now,
        },
        {
            "name": "Docs Template",
            "description": "Шаблон для документации и обучающих материалов.",
            "status": "active",
            "metadata": {"owner": "docs-team"},
            "block": None,
            "created_at": now,
        },
        {
            "name": "Customer Portal",
            "description": "Витрина клиентских возможностей и каталог сервисов.",
            "status": "active",
            "metadata": {"owner": "product", "priority": "high"},
            "block": "UI Library",
            "created_at": now,
        },
        {
            "name": "Security Dashboard",
            "description": "Мониторинг аномалий и событий безопасности.",
            "status": "active",
            "metadata": {"owner": "secops"},
            "block": "Authentication Module",
            "created_at": now,
        },
        {
            "name": "Data Insights Workspace",
            "description": "Рабочее место аналитика с интерактивными отчётами.",
            "status": "draft",
            "metadata": {"owner": "analytics-team"},
            "block": "Reporting Service",
            "created_at": now,
        },
        {
            "name": "Mobile Companion",
            "description": "Мобильное приложение с оффлайн-доступом.",
            "status": "draft",
            "metadata": {"owner": "mobile"},
            "block": "Notification Service",
            "created_at": now,
        },
    ]

    created: Dict[str, Dict[str, str]] = {}
    for config in designs_config:
        block_name = config.get("block")
        block_id = blocks[block_name]["id"] if block_name else None
        payload = {key: value for key, value in config.items() if key != "block"}
        design = repository.create(payload, block_id=block_id)
        created[config["name"]] = design
    return created


def _create_design_edge(session_manager: SessionManager, source_id: str, target_id: str, relation_type: str) -> str | None:
    payload = json.dumps({"relation_type": relation_type}, ensure_ascii=False)
    with session_manager.cursor() as cursor:
        cursor.execute(
            "INSERT INTO mg_designs.design_edge (start_id, end_id, properties) "
            "VALUES (%s::graphid, %s::graphid, %s::agtype) "
            "RETURNING id::text AS edge_id",
            (source_id, target_id, payload),
        )
        row = cursor.fetchone()
    return row["edge_id"] if row else None


def seed_design_edges(session_manager: SessionManager, designs: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    edges_config = [
        ("Project Atlas", "Prototype Nova", "depends_on"),
        ("Customer Portal", "Docs Template", "extends"),
        ("Security Dashboard", "Project Atlas", "observes"),
        ("Data Insights Workspace", "Project Atlas", "references"),
        ("Mobile Companion", "Security Dashboard", "depends_on"),
    ]

    created_edges: Dict[str, str] = {}
    for source_name, target_name, relation_type in edges_config:
        source = designs.get(source_name)
        target = designs.get(target_name)
        if not source or not target:
            continue
        edge_id = _create_design_edge(session_manager, source["id"], target["id"], relation_type)
        if edge_id:
            created_edges[f"{source_name}->{target_name}"] = edge_id
    return created_edges


def seed_projects(
    repository: ProjectsRepository,
    session_manager: SessionManager,
    designs: Dict[str, Dict[str, str]],
    design_edges: Dict[str, str],
) -> List[Dict[str, str]]:
    projects_config = [
        {
            "name": "Reference Implementation",
            "description": "Проект для демонстрации связей дизайнов и блоков.",
            "edges": ["Project Atlas->Prototype Nova"],
        },
        {
            "name": "Customer Rollout",
            "description": "Продуктовая поставка с клиентским порталом и документацией.",
            "edges": [
                "Customer Portal->Docs Template",
                "Project Atlas->Prototype Nova",
            ],
        },
        {
            "name": "Analytics Enablement",
            "description": "Проект по внедрению аналитических отчётов и наблюдения.",
            "edges": [
                "Security Dashboard->Project Atlas",
                "Data Insights Workspace->Project Atlas",
            ],
        },
        {
            "name": "Mobile Pilot",
            "description": "Пилотное мобильное приложение для push-уведомлений и аналитики.",
            "edges": [
                "Mobile Companion->Security Dashboard",
                "Customer Portal->Docs Template",
            ],
        },
    ]

    created_projects: List[Dict[str, str]] = []
    for config in projects_config:
        project = repository.create(
            {
                "name": config["name"],
                "description": config["description"],
            }
        )
        edge_ids = [design_edges[edge_key] for edge_key in config["edges"] if edge_key in design_edges]
        if edge_ids:
            repository.set_design_edge_ids(project["id"], edge_ids)
            project["design_edge_ids"] = edge_ids
        else:
            project["design_edge_ids"] = []
        created_projects.append(project)
    return created_projects


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo data for the multigraph project.")
    parser.add_argument(
        "--dsn",
        help="PostgreSQL DSN (defaults to FEDOC_DATABASE_URL or settings file).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()

    dsn = args.dsn or os.getenv("FEDOC_DATABASE_URL")
    if not dsn:
        settings = Settings.from_env()
        dsn = settings.database_url

    if not dsn:
        print("Database DSN is not provided. Use --dsn or set FEDOC_DATABASE_URL.", file=sys.stderr)
        return 1

    if not args.force:
        answer = input(
            "This will remove data from mg_blocks, mg_designs and mg.design_to_block. Continue? [y/N] "
        ).strip()
        if answer.lower() not in ("y", "yes"):
            print("Aborted.")
            return 0

    print("Using DSN:", dsn)

    session_manager = SessionManager(dsn)
    settings = Settings.from_env()
    blocks_repository = BlocksRepository(session_manager, settings=settings)
    designs_repository = DesignsRepository(session_manager, settings=settings)
    projects_repository = ProjectsRepository(session_manager, settings=settings)

    print("Clearing existing graph data...")
    _ensure_graph_empty(session_manager, settings.graph_blocks_name)
    _ensure_graph_empty(session_manager, settings.graph_designs_name)
    _clear_relational_links(session_manager)

    print("Seeding sample blocks...")
    blocks = seed_blocks(blocks_repository)
    print(f"Inserted {len(blocks)} blocks.")

    print("Seeding sample designs...")
    designs = seed_designs(designs_repository, blocks)
    print(f"Inserted {len(designs)} designs.")

    print("Creating design relations...")
    design_edges = seed_design_edges(session_manager, designs)
    print(f"Inserted {len(design_edges)} design edges.")

    print("Seeding sample project...")
    projects = seed_projects(projects_repository, session_manager, designs, design_edges)
    print(f"Inserted {len(projects)} projects.")

    print("Seed data successfully loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

