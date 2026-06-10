import base64
import importlib
import json

import pytest
from fastapi.testclient import TestClient

VALID = dict(
    athlete_id="882231", api_key="abcd1234efgh5678",
    start="2026-01-01", end="2026-03-01",
)


def parse_ndjson(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.fixture
def client(monkeypatch):
    # Reload app under mock mode with a high rate limit so tests don't trip it.
    monkeypatch.setenv("MOCK_FETCH", "1")
    monkeypatch.setenv("RATE_LIMIT", "1000/hour")
    from app import config
    importlib.reload(config)
    from app import main
    importlib.reload(main)
    return TestClient(main.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["mock"] is True


def test_run_streams_progress_then_json(client):
    r = client.post("/api/run", json=VALID)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")

    events = parse_ndjson(r.text)
    assert any(e["type"] == "progress" for e in events)

    done = events[-1]
    assert done["type"] == "done" and done["filename"] == "training_data.json"
    payload = json.loads(base64.b64decode(done["file_b64"]))
    assert "meta" in payload and "activities" in payload


def test_run_rejects_invalid_payload(client):
    r = client.post("/api/run", json={**VALID, "athlete_id": "nope"})
    assert r.status_code == 422


def test_run_rejects_extra_field(client):
    r = client.post("/api/run", json={**VALID, "injection": "x"})
    assert r.status_code == 422


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_run_failure_surfaces_error_event(client, monkeypatch):
    from app import main

    def boom(*a, **k):
        raise main.runner.RunError("fetch failed (exit 1): bad key")
        yield  # pragma: no cover  (make this a generator)

    monkeypatch.setattr(main.runner, "run_streaming", boom)
    r = client.post("/api/run", json=VALID)
    assert r.status_code == 200
    events = parse_ndjson(r.text)
    assert events[-1]["type"] == "error" and "fetch failed" in events[-1]["message"]


def test_rate_limit_enforced(monkeypatch):
    monkeypatch.setenv("MOCK_FETCH", "1")
    monkeypatch.setenv("RATE_LIMIT", "2/hour")
    from app import config
    importlib.reload(config)
    from app import main
    importlib.reload(main)
    c = TestClient(main.app)
    codes = [c.post("/api/run", json=VALID).status_code for _ in range(3)]
    assert codes.count(429) >= 1
