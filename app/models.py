from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


JSONColumn = JSON().with_variant(JSONB(), "postgresql")


class Camera(db.Model):
    __tablename__ = "cameras"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    name = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(128))
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    events = db.relationship(
        "MotionEvent", back_populates="camera", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "owner_id": self.owner_id,
            "name": self.name,
            "location": self.location,
            "is_online": self.is_online,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    hashed_pass = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def set_password(self, password: str) -> None:
        # werkzeug uses pbkdf2-sha256 by default — salted, slow, no extra deps.
        self.hashed_pass = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_pass, password)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "is_admin": self.is_admin}


class MotionEvent(db.Model):
    """Append-only, immutable. Ingest writes once; nothing updates this table.
    At MVP scale this lives in the relational DB; at production scale it moves
    to a wide-column store (see system design). ML classification does not
    write back here — it produces alerts (see Alert)."""
    __tablename__ = "motion_events"

    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(
        db.Integer, db.ForeignKey("cameras.id"), nullable=False, index=True
    )
    # Client-supplied UUID for idempotency. Camera retries with the same
    # event_id_client; ingest dedupes on (camera_id, event_id_client).
    event_id_client = db.Column(db.String(64), nullable=False)
    detected_at = db.Column(db.DateTime, nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)         # camera's own motion confidence
    video_url = db.Column(db.String(512))                    # blob storage location
    raw_payload = db.Column(JSONColumn)                      # device-specific extras

    camera = db.relationship("Camera", back_populates="events")

    __table_args__ = (
        db.Index("ix_events_camera_time", "camera_id", "detected_at"),
        # idempotency: the same client event from the same camera is one row
        db.UniqueConstraint("camera_id", "event_id_client", name="uq_events_camera_event_id_client"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "event_id_client": self.event_id_client,
            "detected_at": self.detected_at.isoformat(),
            "confidence": self.confidence,
            "video_url": self.video_url,
            "raw_payload": self.raw_payload,
        }


class Alert(db.Model):
    """Carries ML classification + delivery audit. One row per (event, user, channel).
    Written by the ML pipeline when an event scores >= threshold; mutated by
    the notify service to set delivered_at when the user app acks."""
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer, db.ForeignKey("motion_events.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    ml_score = db.Column(db.Float, nullable=False)           # ML classifier confidence
    ml_label = db.Column(db.String(32), nullable=False)      # e.g. "person", "vehicle", "package"
    channel = db.Column(db.String(16), nullable=False)       # "websocket" | "push"
    sent_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    delivered_at = db.Column(db.DateTime)                    # null until ack received

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "ml_score": self.ml_score,
            "ml_label": self.ml_label,
            "channel": self.channel,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }