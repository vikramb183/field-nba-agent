from fastapi.testclient import TestClient

from app.api import create_app


def client(store, cache):
    return TestClient(create_app(store=store, cache=cache))


def test_health(store, cache):
    r = client(store, cache).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_next_best_action(store, cache):
    r = client(store, cache).post("/next-best-action", json={
        "device_type": "ont", "description": "No internet and a red LOS light"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["recommendation"]["cause_id"] == "fiber_damage"
    assert body["trace"]


def test_rejects_unknown_device(store, cache):
    r = client(store, cache).post("/next-best-action", json={"device_type": "toaster", "description": "no power"})
    assert r.status_code == 422


def test_rejects_empty_description(store, cache):
    r = client(store, cache).post("/next-best-action", json={"device_type": "ont", "description": ""})
    assert r.status_code == 422


def test_workflow_diagram(store, cache):
    r = client(store, cache).get("/workflow")
    assert r.status_code == 200
    assert "triage_agent" in r.json()["mermaid"]
