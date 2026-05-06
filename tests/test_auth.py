import pytest

from app.extensions import db
from app.models import User


@pytest.fixture
def admin(app):
    with app.app_context():
        user = User(email="admin@example.com", is_admin=True)
        user.set_password("admin")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def non_admin(app):
    with app.app_context():
        user = User(email="alice@example.com", is_admin=False)
        user.set_password("alice")
        db.session.add(user)
        db.session.commit()
        return user


def test_login_requires_email_and_password(client):
    resp = client.post("/auth/login", json={})
    assert resp.status_code == 400


def test_login_unknown_user_returns_401(client):
    resp = client.post(
        "/auth/login", json={"email": "nope@example.com", "password": "x"}
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "invalid_credentials"


def test_login_wrong_password_returns_401(client, admin):
    resp = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_returns_token_with_8h_ttl(client, admin):
    resp = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "admin"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 8 * 3600
    assert body["user"]["is_admin"] is True
    assert "access_token" in body


def test_token_works_for_event_ingest(client, admin):
    login = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "admin"}
    )
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers=headers,
    )

    import uuid

    resp = client.post(
        "/events",
        json={"device_id": "cam-1", "event_id_client": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 201


def test_admin_only_endpoints_reject_non_admin(client, non_admin):
    login = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "alice"}
    )
    token = login.get_json()["access_token"]

    resp = client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"


def test_me_endpoint_echoes_claims(client, admin):
    login = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "admin"}
    )
    token = login.get_json()["access_token"]

    resp = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["email"] == "admin@example.com"
    assert body["is_admin"] is True
