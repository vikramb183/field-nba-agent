import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.graph_store import InMemoryGraphStore


def test_success_raises_rate_and_failure_lowers_it():
    store = InMemoryGraphStore()
    up = store.record_outcome("wifi_interference", "change_wifi_channel", success=True)
    assert up["success_rate"] == pytest.approx((0.70 * 10 + 1) / 11)   # 0.727
    down = store.record_outcome("wifi_interference", "change_wifi_channel", success=False)
    assert down["success_rate"] == pytest.approx((0.70 * 10 + 1) / 12)  # 0.667
    assert down["attempts"] == 2 and down["successes"] == 1


def test_unknown_pair_returns_none():
    assert InMemoryGraphStore().record_outcome("fiber_damage", "change_wifi_channel", True) is None


def test_feedback_changes_the_next_recommendation(store, cache):
    client = TestClient(create_app(store=store, cache=cache))
    ticket = {"device_type": "router", "description": "Wi-Fi keeps dropping and speeds are slow"}

    before = client.post("/next-best-action", json=ticket).json()
    assert before["recommendation"]["action_id"] == "change_wifi_channel"

    r = client.post("/feedback", json={
        "cause_id": "wifi_interference", "action_id": "change_wifi_channel", "success": False})
    assert r.status_code == 200
    assert r.json()["success_rate"] < 0.70

    after = client.post("/next-best-action", json=ticket).json()
    assert after["cache_hit"] is False            # feedback cleared the stale cache
    assert after["recommendation"]["action_id"] == "add_mesh_extender"


def test_feedback_unknown_pair_is_404(store, cache):
    client = TestClient(create_app(store=store, cache=cache))
    r = client.post("/feedback", json={"cause_id": "nope", "action_id": "nope", "success": True})
    assert r.status_code == 404