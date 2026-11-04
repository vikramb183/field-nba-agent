"""Graph retrieval: Neo4j in production, an in-memory twin for tests and local runs.

Both stores answer the same question: for a device type and a set of
symptoms, which actions could fix the likely causes?
"""
from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app import sample_data as sd

CANDIDATES_CYPHER = """
MATCH (s:Symptom)-[i:INDICATES]->(c:Cause)-[:AFFECTS]->(:DeviceType {id: $device_type})
WHERE s.id IN $symptom_ids
WITH c, sum(i.weight) AS cause_score
MATCH (c)-[r:RESOLVED_BY]->(a:Action)
RETURN a.id AS action_id, a.name AS action, a.steps AS steps,
       a.est_minutes AS est_minutes, a.requires_escalation AS requires_escalation,
       r.success_rate AS success_rate, c.id AS cause_id, c.name AS cause, cause_score
ORDER BY cause_score * success_rate DESC, action_id
LIMIT $limit
"""


class GraphStore(Protocol):
    def find_candidate_actions(self, device_type: str, symptom_ids: list[str], limit: int = 5) -> list[dict]: ...

    def list_symptoms(self) -> list[dict]: ...


class InMemoryGraphStore:
    """Runs the same logic as CANDIDATES_CYPHER over the sample data."""

    def __init__(self) -> None:
        self._symptoms = {s["id"]: s for s in sd.SYMPTOMS}
        self._causes = {c["id"]: c for c in sd.CAUSES}
        self._actions = {a["id"]: a for a in sd.ACTIONS}

    def list_symptoms(self) -> list[dict]:
        return list(self._symptoms.values())

    def find_candidate_actions(self, device_type: str, symptom_ids: list[str], limit: int = 5) -> list[dict]:
        cause_scores: dict[str, float] = defaultdict(float)
        for symptom_id, cause_id, weight in sd.INDICATES:
            if symptom_id in symptom_ids and device_type in self._causes[cause_id]["affects"]:
                cause_scores[cause_id] += weight

        rows = []
        for cause_id, action_id, success_rate in sd.RESOLVED_BY:
            if cause_id not in cause_scores:
                continue
            action, cause = self._actions[action_id], self._causes[cause_id]
            rows.append({
                "action_id": action_id,
                "action": action["name"],
                "steps": action["steps"],
                "est_minutes": action["est_minutes"],
                "requires_escalation": action["requires_escalation"],
                "success_rate": success_rate,
                "cause_id": cause_id,
                "cause": cause["name"],
                "cause_score": round(cause_scores[cause_id], 3),
            })
        rows.sort(key=lambda r: (-r["cause_score"] * r["success_rate"], r["action_id"]))
        return rows[:limit]


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase  # imported lazily so tests don't need a server

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def list_symptoms(self) -> list[dict]:
        records, _, _ = self._driver.execute_query(
            "MATCH (s:Symptom) RETURN s.id AS id, s.name AS name, s.keywords AS keywords ORDER BY id"
        )
        return [r.data() for r in records]

    def find_candidate_actions(self, device_type: str, symptom_ids: list[str], limit: int = 5) -> list[dict]:
        records, _, _ = self._driver.execute_query(
            CANDIDATES_CYPHER, device_type=device_type, symptom_ids=symptom_ids, limit=limit
        )
        return [r.data() for r in records]
