from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health():
    return jsonify(status="ok")

@health_bp.route("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ready")
    except Exception:
        return jsonify(status="not_ready"), 503