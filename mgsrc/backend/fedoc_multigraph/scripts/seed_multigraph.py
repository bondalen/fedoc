"""Seed utility for multigraph demo data."""
from __future__ import annotations

import argparse
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict

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


def seed_projects(repository: ProjectsRepository, session_manager: SessionManager, designs: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    design_items = list(designs.values())
    edge_id = None
    if len(design_items) >= 2:
        edge_id = _create_design_edge(session_manager, design_items[0]["id"], design_items[1]["id"], "references")

    project = repository.create(
        {
            "name": "Reference Implementation",
            "description": "Проект для демонстрации связей дизайнов и блоков.",
        }
    )
    if edge_id:
        repository.set_design_edge_ids(project["id"], [edge_id])
        project["design_edge_ids"] = [edge_id]
    else:
        project["design_edge_ids"] = []
    return {"project": project, "design_edge_id": edge_id}


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

    print("Seeding sample project...")
    project_data = seed_projects(projects_repository, session_manager, designs)
    print("Inserted 1 project.")

    print("Seed data successfully loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

