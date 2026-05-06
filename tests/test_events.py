import uuid


def test_ingest_requires_auth(client):
    resp = client.post(
        "/events",
        json={"device_id": "cam-1", "event_id_client": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


def test_ingest_requires_event_id_client(client, auth_header):
    resp = client.post("/events", json={"device_id": "cam-1"}, headers=auth_header)
    assert resp.status_code == 400


def test_ingest_unknown_device_returns_404(client, auth_header):
    resp = client.post(
        "/events",
        json={"device_id": "ghost", "event_id_client": str(uuid.uuid4())},
        headers=auth_header,
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "unknown_device"


def test_ingest_then_read_round_trip(client, auth_header, admin_token):
    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    event_id = str(uuid.uuid4())
    resp = client.post(
        "/events",
        json={
            "device_id": "cam-1",
            "event_id_client": event_id,
            "confidence": 0.92,
            "video_url": "blob://clips/cam-1/2026-05-07T12-00-00.mp4",
            "payload": {"zone": "porch"},
        },
        headers=auth_header,
    )
    assert resp.status_code == 201
    body = resp.get_json()["event"]
    assert body["confidence"] == 0.92
    assert body["video_url"].endswith(".mp4")
    assert "ml_score" not in body                # ML output lives on Alert, not Event
    assert body["raw_payload"] == {"zone": "porch"}


def test_ingest_is_idempotent_on_event_id_client(client, auth_header, admin_token):
    """Camera retry with the same event_id_client must not duplicate the row."""
    client.post(
        "/cameras",
        json={"device_id": "cam-1", "name": "Front Door"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    payload = {
        "device_id": "cam-1",
        "event_id_client": str(uuid.uuid4()),
        "confidence": 0.9,
    }
    first = client.post("/events", json=payload, headers=auth_header)
    second = client.post("/events", json=payload, headers=auth_header)

    assert first.status_code == 201
    assert second.status_code == 200             # replay → 200, not 201
    assert first.get_json()["event"]["id"] == second.get_json()["event"]["id"]