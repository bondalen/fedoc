"""Blueprint providing CRUD for mg_blocks graph."""
from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from ..services import get_blocks_service
from ..validators import validate_json, validate_query
from ..validators.blocks import BlockCreateSchema, BlockQuerySchema, BlockUpdateSchema

blocks_bp = Blueprint("blocks", __name__, url_prefix="/api/blocks")


@blocks_bp.get("/")
def list_blocks():
    """Return paginated blocks."""

    query = validate_query(BlockQuerySchema, request.args)
    service = get_blocks_service()
    result = service.list_blocks(query)
    return jsonify(result), HTTPStatus.OK


@blocks_bp.get("/<block_id>")
def get_block(block_id: str):
    """Return a single block by id."""

    service = get_blocks_service()
    block = service.get_block(block_id)
    return jsonify(block), HTTPStatus.OK


@blocks_bp.post("/")
def create_block():
    """Create a block vertex (optionally linking to a parent)."""

    payload = validate_json(BlockCreateSchema, request)
    service = get_blocks_service()
    block = service.create_block(payload)
    return jsonify(block), HTTPStatus.CREATED


@blocks_bp.patch("/<block_id>")
def patch_block(block_id: str):
    """Update mutable block properties."""

    payload = validate_json(BlockUpdateSchema, request)
    service = get_blocks_service()
    block = service.update_block(block_id, payload)
    return jsonify(block), HTTPStatus.OK


@blocks_bp.delete("/<block_id>")
def delete_block(block_id: str):
    """Delete a block and its relations."""

    service = get_blocks_service()
    service.delete_block(block_id)
    return ("", HTTPStatus.NO_CONTENT)

