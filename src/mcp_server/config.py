"""
Конфигурация MCP-сервера fedoc
"""

import os
from pathlib import Path

# Пути проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SRC_DIR = PROJECT_ROOT / "src"
DEV_DIR = PROJECT_ROOT / "dev"

# ArangoDB конфигурация
ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "fedoc")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

# Граф проектов
COMMON_GRAPH_NAME = "common_project_graph"

# Коллекции
PROJECTS_COLLECTION = "projects"
CANONICAL_NODES_COLLECTION = "canonical_nodes"
RULES_COLLECTION = "rules"
TEMPLATES_COLLECTION = "templates"
PROJECT_EDGES_COLLECTION = "project_edges"
