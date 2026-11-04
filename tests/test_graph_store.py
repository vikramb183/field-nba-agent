from app.graph_store import InMemoryGraphStore


def test_los_on_ont_points_to_fiber():
    rows = InMemoryGraphStore().find_candidate_actions("ont", ["los_light"])
    assert rows, "expected candidates"
    assert {r["cause_id"] for r in rows} == {"fiber_damage"}
    assert rows[0]["action_id"] == "replace_fiber_patch"  # 0.9 * 0.85 beats 0.9 * 0.70


def test_causes_are_filtered_by_device_type():
    rows = InMemoryGraphStore().find_candidate_actions("small_cell", ["los_light"])
    assert rows == []  # fiber damage only affects ONTs in this graph


def test_cause_scores_add_up_across_symptoms():
    rows = InMemoryGraphStore().find_candidate_actions("router", ["slow_speed", "wifi_drops"])
    wifi = [r for r in rows if r["cause_id"] == "wifi_interference"]
    assert wifi and wifi[0]["cause_score"] == 1.5  # 0.7 + 0.8


def test_limit_is_respected():
    rows = InMemoryGraphStore().find_candidate_actions("router", ["no_internet", "slow_speed", "wifi_drops"], limit=2)
    assert len(rows) == 2
