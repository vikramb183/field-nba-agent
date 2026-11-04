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

# How much the starting success rate counts, measured in "jobs".
# 10 means the seed rate is treated like 10 past jobs, so one bad report
# moves it a little, not all the way to 0.
PRIOR_WEIGHT = 10

RECORD_OUTCOME_CYPHER = """
MATCH (:Cause {id: $cause_id})-[r:RESOLVED_BY]->(:Action {id: $action_id})
SET r.prior_rate = coalesce(r.prior_rate, r.success_rate),
    r.attempts = coalesce(r.attempts, 0) + 1,
    r.successes = coalesce(r.successes, 0) + CASE WHEN $success THEN 1 ELSE 0 END
SET r.success_rate = (r.prior_rate * $prior_weight + r.successes) / ($prior_weight + r.attempts)
RETURN r.success_rate AS success_rate, r.attempts AS attempts, r.successes AS successes
"""


def updated_rate(prior_rate: float, successes: int, attempts: int) -> float:
    return (prior_rate * PRIOR_WEIGHT + successes) / (PRIOR_WEIGHT + attempts)


class GraphStore(Protocol):
    def find_candidate_actions(self, device_type: str, symptom_ids: list[str], limit: int = 5) -> list[dict]: ...

    def list_symptoms(self) -> list[dict]: ...

    def record_outcome(self, cause_id: str, action_id: str, success: bool) -> dict | None: ...


class InMemoryGraphStore:
    """Runs the same logic as CANDIDATES_CYPHER over the sample data."""

    def __init__(self) -> None:
        self._symptoms = {s["id"]: s for s in sd.SYMPTOMS}
        self._causes = {c["id"]: c for c in sd.CAUSES}
        self._actions = {a["id"]: a for a in sd.ACTIONS}
        # Copy the fix edges so feedback can change them without touching sample_data.
        self._edges = {
            (cause_id, action_id): {"prior_rate": rate, "success_rate": rate, "attempts": 0, "successes": 0}
            for cause_id, action_id, rate in sd.RESOLVED_BY
        }

    def list_symptoms(self) -> list[dict]:
        return list(self._symptoms.values())

    def record_outcome(self, cause_id: str, action_id: str, success: bool) -> dict | None:
        edge = self._edges.get((cause_id, action_id))
        if edge is None:
            return None
        edge["attempts"] += 1
        edge["successes"] += int(success)
        edge["success_rate"] = updated_rate(edge["prior_rate"], edge["successes"], edge["attempts"])
        return {k: edge[k] for k in ("success_rate", "attempts", "successes")}

    def find_candidate_actions(self, device_type: str, symptom_ids: list[str], limit: int = 5) -> list[dict]:
        cause_scores: dict[str, float] = defaultdict(float)
        for symptom_id, cause_id, weight in sd.INDICATES:
            if symptom_id in symptom_ids and device_type in self._causes[cause_id]["affects"]:
                cause_scores[cause_id] += weight

        rows = []
        for (cause_id, action_id), edge in self._edges.items():
            if cause_id not in cause_scores:
                continue
            success_rate = edge["success_rate"]
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

    def record_outcome(self, cause_id: str, action_id: str, success: bool) -> dict | None:
        records, _, _ = self._driver.execute_query(
            RECORD_OUTCOME_CYPHER, cause_id=cause_id, action_id=action_id,
            success=success, prior_weight=PRIOR_WEIGHT,
        )
        return records[0].data() if records else None