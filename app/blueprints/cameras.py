from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..auth import admin_required
from ..extensions import db
from ..models import Camera
from ..errors import AppError

cameras_bp = Blueprint("cameras", __name__)


@cameras_bp.route("", methods=["GET"])
@jwt_required()
def list_cameras():
    cameras = Camera.query.order_by(Camera.created_at.desc()).all()
    return jsonify(cameras=[c.to_dict() for c in cameras])

@cameras_bp.route("/<int:camera_id>", methods=["GET"])
@jwt_required()
def get_camera(camera_id: int):
    camera = db.session.get(Camera, camera_id)
    if camera is None:
        raise AppError("camera not found", status_code=404, code="camera_not_found")
    return jsonify(camera=camera.to_dict())


@cameras_bp.route("", methods=["POST"])
@admin_required
def create_camera():
    data = request.get_json() or {}
    if not data.get("device_id") or not data.get("name"):
        raise AppError("device_id and name are required", code="validation")

    if Camera.query.filter_by(device_id=data["device_id"]).first():
        raise AppError("device_id already registered", status_code=409, code="conflict")

    # owner_id drives "who gets alerted" downstream — pull it from the JWT
    # identity so admins implicitly own the cameras they register.
    try:
        owner_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        owner_id = None

    camera = Camera(
        device_id=data["device_id"],
        name=data["name"],
        location=data.get("location"),
        owner_id=owner_id,
    )
    db.session.add(camera)
    db.session.commit()
    return jsonify(camera=camera.to_dict()), 201