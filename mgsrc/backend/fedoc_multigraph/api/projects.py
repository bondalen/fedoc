"""Blueprint providing CRUD for projects."""
from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from ..services import get_projects_service
from ..validators import validate_json, validate_query
from ..validators.projects import ProjectCreateSchema, ProjectQuerySchema, ProjectUpdateSchema

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@projects_bp.get("/")
def list_projects():
    query = validate_query(ProjectQuerySchema, request.args)
    service = get_projects_service()
    result = service.list_projects(query)
    return jsonify(result), HTTPStatus.OK


@projects_bp.get("/<int:project_id>")
def get_project(project_id: int):
    service = get_projects_service()
    project = service.get_project(project_id)
    return jsonify(project), HTTPStatus.OK


@projects_bp.post("/")
def create_project():
    payload = validate_json(ProjectCreateSchema, request)
    service = get_projects_service()
    project = service.create_project(payload)
    return jsonify(project), HTTPStatus.CREATED


@projects_bp.patch("/<int:project_id>")
def patch_project(project_id: int):
    payload = validate_json(ProjectUpdateSchema, request)
    service = get_projects_service()
    project = service.update_project(project_id, payload)
    return jsonify(project), HTTPStatus.OK


@projects_bp.delete("/<int:project_id>")
def delete_project(project_id: int):
    service = get_projects_service()
    service.delete_project(project_id)
    return ("", HTTPStatus.NO_CONTENT)


@projects_bp.get("/<int:project_id>/graph")
def get_project_graph(project_id: int):
    service = get_projects_service()
    graph = service.get_project_graph(project_id)
    return jsonify(graph), HTTPStatus.OK

