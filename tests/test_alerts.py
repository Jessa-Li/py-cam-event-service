"""End-to-end tests for the ML → alert → notify pipeline."""
import uuid

import pytest

from app.extensions import db
from app.models import User


@pytest.fixture
def admin_login(client):
    """Seed an admin user and return (token, user_id)."""
    user = User(email="owner@example.com", is_admin=True)
    user.set_password("pw")
    db.session.add(user)
    db.session.commit()
    user_id = user.id

    resp = client.post(
        "/auth/login", json={"email": "owner@example.com", "password": "pw"}
    )
    return resp.get_json()["access_token"], user_id


@pytest.fixture
def other_user_login(client):
    user = User(email="other@example.com", is_admin=True)
    user.set_password("pw")
    db.session.add(user)
    db.session.commit()
    resp = client.post(
        "/auth/login", json={"email": "other@example.com", "password": "pw"}
    )
    return resp.get_json()["access_token"], user.id


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_high_confidence_event_creates_alert_for_camera_owner(client, admin_login, monkeypatch):
    token, user_id = admin_login
    # Force the classifier to fire (confidence is high; we additionally pin
    # randomness so the score lands above THRESHOLD deterministically).
    monkeypatch.setattr("app.classifier.random.uniform", lambda a, b: 0.0)

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=_h(token),
    )
    client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": str(uuid.uuid4()),
            "confidence": 0.95,
            "payload": {"zone": "porch"},
        },
        headers=_h(token),
    )

    resp = client.get("/alerts/recent", headers=_h(token))
    assert resp.status_code == 200
    alerts = resp.get_json()["alerts"]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["user_id"] == user_id
    assert alert["ml_label"] in {"package", "person", "vehicle"}  # porch pool
    assert alert["ml_score"] >= 0.7
    assert alert["delivered_at"] is None
    assert alert["camera"]["device_id"] == "cam-1"


def test_low_confidence_event_does_not_alert(client, admin_login, monkeypatch):
    token, _ = admin_login
    # Negative jitter pushes score below the threshold deterministically.
    monkeypatch.setattr("app.classifier.random.uniform", lambda a, b: -0.1)

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=_h(token),
    )
    client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": str(uuid.uuid4()),
            "confidence": 0.5,
        },
        headers=_h(token),
    )

    resp = client.get("/alerts/recent", headers=_h(token))
    assert resp.status_code == 200
    assert resp.get_json()["alerts"] == []


def test_users_only_see_their_own_alerts(client, admin_login, other_user_login, monkeypatch):
    owner_token, _ = admin_login
    other_token, _ = other_user_login
    monkeypatch.setattr("app.classifier.random.uniform", lambda a, b: 0.0)

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=_h(owner_token),
    )
    client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": str(uuid.uuid4()),
            "confidence": 0.95,
        },
        headers=_h(owner_token),
    )

    # Owner sees one alert; the other user, registered separately, sees none.
    assert len(client.get("/alerts/recent", headers=_h(owner_token)).get_json()["alerts"]) == 1
    assert client.get("/alerts/recent", headers=_h(other_token)).get_json()["alerts"] == []


def test_ack_sets_delivered_at_and_is_idempotent(client, admin_login, monkeypatch):
    token, _ = admin_login
    monkeypatch.setattr("app.classifier.random.uniform", lambda a, b: 0.0)

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=_h(token),
    )
    client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": str(uuid.uuid4()),
            "confidence": 0.95,
        },
        headers=_h(token),
    )
    alert_id = client.get("/alerts/recent", headers=_h(token)).get_json()["alerts"][0]["id"]

    first = client.post(f"/alerts/{alert_id}/ack", headers=_h(token))
    assert first.status_code == 200
    delivered_at = first.get_json()["alert"]["delivered_at"]
    assert delivered_at is not None

    # Re-ack is a no-op, original timestamp stands.
    second = client.post(f"/alerts/{alert_id}/ack", headers=_h(token))
    assert second.status_code == 200
    assert second.get_json()["alert"]["delivered_at"] == delivered_at


def test_ack_other_users_alert_returns_404(client, admin_login, other_user_login, monkeypatch):
    owner_token, _ = admin_login
    other_token, _ = other_user_login
    monkeypatch.setattr("app.classifier.random.uniform", lambda a, b: 0.0)

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=_h(owner_token),
    )
    client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": str(uuid.uuid4()),
            "confidence": 0.95,
        },
        headers=_h(owner_token),
    )
    alert_id = client.get("/alerts/recent", headers=_h(owner_token)).get_json()["alerts"][0]["id"]

    resp = client.post(f"/alerts/{alert_id}/ack", headers=_h(other_token))
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "alert_not_found"
