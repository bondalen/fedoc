"""Blueprint providing CRUD for mg_designs graph."""
from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from ..services import get_designs_service
from ..validators import validate_json, validate_query
from ..validators.designs import DesignCreateSchema, DesignQuerySchema, DesignUpdateSchema

designs_bp = Blueprint("designs", __name__, url_prefix="/api/designs")


@designs_bp.get("/")
def list_designs():
    query = validate_query(DesignQuerySchema, request.args)
    service = get_designs_service()
    result = service.list_designs(query)
    return jsonify(result), HTTPStatus.OK


@designs_bp.get("/<design_id>")
def get_design(design_id: str):
    service = get_designs_service()
    design = service.get_design(design_id)
    return jsonify(design), HTTPStatus.OK


@designs_bp.post("/")
def create_design():
    payload = validate_json(DesignCreateSchema, request)
    service = get_designs_service()
    design = service.create_design(payload)
    return jsonify(design), HTTPStatus.CREATED


@designs_bp.patch("/<design_id>")
def patch_design(design_id: str):
    payload = validate_json(DesignUpdateSchema, request)
    service = get_designs_service()
    design = service.update_design(design_id, payload)
    return jsonify(design), HTTPStatus.OK


@designs_bp.delete("/<design_id>")
def delete_design(design_id: str):
    service = get_designs_service()
    service.delete_design(design_id)
    return ("", HTTPStatus.NO_CONTENT)

