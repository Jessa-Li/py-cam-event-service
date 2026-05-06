from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required

from ..classifier import classify
from ..extensions import db, cache, limiter
from ..models import Alert, Camera, MotionEvent
from ..errors import AppError

events_bp = Blueprint("events", __name__)


@events_bp.route("", methods=["POST"])
@jwt_required()
# A well-behaved camera fires a handful of events per minute at most. 60/min
# per camera (keyed by JWT identity via the default `rate_limit_key`) gives
# plenty of headroom while capping a stuck-firmware device that fires in a
# tight loop. Beyond this we'd rely on per-camera quotas at the gateway.
@limiter.limit("60 per minute")
def ingest_event():
    """Called by a camera when motion is detected.

    Idempotent: cameras retry with the same event_id_client, and we dedupe
    on (camera_id, event_id_client). At production scale this handler would
    publish to a message queue rather than writing the row directly; the
    dedupe check moves to the consumer.
    """
    data = request.get_json() or {}
    device_id = data.get("device_id")
    event_id_client = data.get("event_id_client")
    if not device_id or not event_id_client:
        raise AppError("device_id and event_id_client are required", code="validation")

    camera = Camera.query.filter_by(device_id=device_id).first()
    if camera is None:
        raise AppError("unknown device", status_code=404, code="unknown_device")

    # Idempotency: replay returns 200 with the existing row, never duplicates.
    existing = MotionEvent.query.filter_by(
        camera_id=camera.id, event_id_client=event_id_client
    ).first()
    if existing:
        return jsonify(event=existing.to_dict()), 200

    detected_at = (
        datetime.fromisoformat(data["detected_at"])
        if data.get("detected_at")
        else datetime.now(timezone.utc)
    )

    event = MotionEvent(
        camera_id=camera.id,
        event_id_client=event_id_client,
        detected_at=detected_at,
        confidence=float(data.get("confidence", 1.0)),
        video_url=data.get("video_url"),     # blob already uploaded by camera
        raw_payload=data.get("payload"),
    )
    db.session.add(event)
    db.session.commit()

    cache.delete(f"recent_events:{camera.id}")
    current_app.logger.info(
        "motion event ingested",
        extra={
            "ctx_camera_id": camera.id,
            "ctx_event_id": event.id,
            "ctx_event_id_client": event_id_client,
        },
    )

    # Inline classification (MVP). At scale this whole block moves to a queue
    # consumer — the ingest path returns 201 immediately, the classifier
    # worker writes the Alert row asynchronously. The schema doesn't change.
    ml = classify(event.raw_payload, event.confidence)
    if ml is not None and camera.owner_id is not None:
        alert = Alert(
            event_id=event.id,
            user_id=camera.owner_id,
            ml_score=ml["score"],
            ml_label=ml["label"],
            channel="websocket",
        )
        db.session.add(alert)
        db.session.commit()
        cache.delete(f"recent_alerts:{camera.owner_id}")
        current_app.logger.info(
            "alert created",
            extra={
                "ctx_alert_id": alert.id,
                "ctx_event_id": event.id,
                "ctx_user_id": camera.owner_id,
                "ctx_ml_label": ml["label"],
                "ctx_ml_score": ml["score"],
            },
        )

    return jsonify(event=event.to_dict()), 201


@events_bp.route("/by-camera/<int:camera_id>/recent", methods=["GET"])
@cache.memoize(timeout=15)
def recent_events(camera_id: int):
    """Cached read of the last hour of motion events for a camera."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    events = (
        MotionEvent.query
        .filter(MotionEvent.camera_id == camera_id,
                MotionEvent.detected_at >= since)
        .order_by(MotionEvent.detected_at.desc())
        .limit(100)
        .all()
    )
    return jsonify(events=[e.to_dict() for e in events])