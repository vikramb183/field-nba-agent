"""Runs only when NEO4J_URI is set (GitHub Actions starts a Neo4j service for it).

Checks that the real Cypher query returns the same ranking as the in-memory store.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("NEO4J_URI"), reason="NEO4J_URI not set")

CASES = [
    ("ont", ["los_light"]),
    ("ont", ["no_internet", "los_light"]),
    ("router", ["slow_speed", "wifi_drops"]),
    ("router", ["no_internet", "slow_speed", "wifi_drops"]),
    ("small_cell", ["slow_speed"]),
    ("small_cell", ["los_light"]),
]


@pytest.fixture(scope="module")
def neo4j_store():
    from neo4j import GraphDatabase

    from app.graph_store import Neo4jGraphStore
    from app.seed import seed

    from app.config import get_settings

    settings = get_settings()
    uri = settings.neo4j_uri
    auth = (settings.neo4j_user, settings.neo4j_password)
    with GraphDatabase.driver(uri, auth=auth) as driver:
        driver.execute_query("MATCH (n) DETACH DELETE n")
        seed(driver)
    store = Neo4jGraphStore(uri, *auth)
    yield store
    store.close()


@pytest.mark.parametrize("device,symptoms", CASES)
def test_cypher_matches_in_memory(neo4j_store, device, symptoms):
    from app.graph_store import InMemoryGraphStore

    expected = InMemoryGraphStore().find_candidate_actions(device, symptoms)
    actual = neo4j_store.find_candidate_actions(device, symptoms)
    assert [r["action_id"] for r in actual] == [r["action_id"] for r in expected]
    for a, e in zip(actual, expected):
        assert a["cause_score"] == pytest.approx(e["cause_score"])


def test_symptom_catalog_loaded(neo4j_store):
    assert {s["id"] for s in neo4j_store.list_symptoms()} >= {"no_internet", "los_light"}



def test_feedback_updates_the_edge_in_neo4j(neo4j_store):
    from app.graph_store import InMemoryGraphStore

    memory = InMemoryGraphStore()
    for success in (True, False, False):
        expected = memory.record_outcome("fiber_damage", "clean_inspect_fiber", success)
        actual = neo4j_store.record_outcome("fiber_damage", "clean_inspect_fiber", success)
        assert actual["success_rate"] == pytest.approx(expected["success_rate"])
        assert actual["attempts"] == expected["attempts"]
    assert neo4j_store.record_outcome("fiber_damage", "nope", True) is None
