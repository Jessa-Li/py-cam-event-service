"""Alerts API.

Reads scoped to the current user (you only see your own alerts) and an ack
endpoint that records when the user app received the alert. In production
the notify service would push alerts over WebSocket / APNs / FCM; this MVP
exposes them via polling so the frontend can demonstrate the flow without
a real-time channel.
"""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import Alert, Camera, MotionEvent
from ..errors import AppError

alerts_bp = Blueprint("alerts", __name__)


def _current_user_id() -> int:
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        # Tokens minted with non-numeric identity (e.g. test fixtures using
        # "test-camera") can't own alerts. Treat them as no-such-user.
        raise AppError("alerts require a user-bound token", status_code=403, code="forbidden")


@alerts_bp.route("/recent", methods=["GET"])
@jwt_required()
def recent_alerts():
    """Last 24h of alerts for the current user, joined with event + camera
    so the frontend can render context without follow-up requests."""
    user_id = _current_user_id()
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    rows = (
        db.session.query(Alert, MotionEvent, Camera)
        .join(MotionEvent, Alert.event_id == MotionEvent.id)
        .join(Camera, MotionEvent.camera_id == Camera.id)
        .filter(Alert.user_id == user_id, Alert.sent_at >= since)
        .order_by(Alert.sent_at.desc())
        .limit(50)
        .all()
    )

    return jsonify(alerts=[
        {
            **alert.to_dict(),
            "event": {
                "id": event.id,
                "detected_at": event.detected_at.isoformat(),
                "confidence": event.confidence,
            },
            "camera": {
                "id": camera.id,
                "name": camera.name,
                "device_id": camera.device_id,
                "location": camera.location,
            },
        }
        for alert, event, camera in rows
    ])


@alerts_bp.route("/<int:alert_id>/ack", methods=["POST"])
@jwt_required()
def ack_alert(alert_id: int):
    """Record that the client received this alert. Idempotent: re-acking is
    a no-op, the original delivered_at stands."""
    user_id = _current_user_id()
    alert = db.session.get(Alert, alert_id)
    # Don't leak existence of someone else's alert id — same 404 response.
    if alert is None or alert.user_id != user_id:
        raise AppError("alert not found", status_code=404, code="alert_not_found")

    if alert.delivered_at is None:
        alert.delivered_at = datetime.now(timezone.utc)
        db.session.commit()
        current_app.logger.info(
            "alert acked",
            extra={"ctx_alert_id": alert.id, "ctx_user_id": user_id},
        )

    return jsonify(alert=alert.to_dict())
