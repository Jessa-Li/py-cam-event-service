"""Rate limiting is RATELIMIT_ENABLED=False in TestingConfig so unrelated
tests don't trip limits. These tests flip it on at the config class so the
limiter is built in the enabled state during create_app."""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db, limiter


@pytest.fixture
def limited_app(monkeypatch):
    monkeypatch.setattr(TestingConfig, "RATELIMIT_ENABLED", True)
    app = create_app("testing")
    with app.app_context():
        limiter.reset()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def limited_client(limited_app):
    return limited_app.test_client()


def test_login_rate_limited_after_5_attempts(limited_client):
    payload = {"email": "nope@example.com", "password": "x"}
    # First 5 hits are 401 (bad credentials). The 6th should be 429.
    for _ in range(5):
        resp = limited_client.post("/auth/login", json=payload)
        assert resp.status_code == 401

    resp = limited_client.post("/auth/login", json=payload)
    assert resp.status_code == 429
    body = resp.get_json()
    assert body["error"] == "rate_limited"
    assert "request_id" in body
