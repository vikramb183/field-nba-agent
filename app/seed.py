"""Load the sample knowledge graph into Neo4j.

Usage:  python -m app.seed
"""
from __future__ import annotations

from neo4j import GraphDatabase

from app import sample_data as sd
from app.config import get_settings

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:DeviceType) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Symptom) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Cause) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Action) REQUIRE n.id IS UNIQUE",
]


def seed(driver) -> None:
    for stmt in CONSTRAINTS:
        driver.execute_query(stmt)

    driver.execute_query("UNWIND $rows AS r MERGE (d:DeviceType {id: r.id}) SET d.name = r.name",
                         rows=sd.DEVICE_TYPES)
    driver.execute_query("UNWIND $rows AS r MERGE (s:Symptom {id: r.id}) SET s.name = r.name, s.keywords = r.keywords",
                         rows=sd.SYMPTOMS)
    driver.execute_query(
        "UNWIND $rows AS r MERGE (a:Action {id: r.id}) "
        "SET a.name = r.name, a.steps = r.steps, a.est_minutes = r.est_minutes, "
        "a.requires_escalation = r.requires_escalation",
        rows=sd.ACTIONS,
    )
    driver.execute_query(
        "UNWIND $rows AS r MERGE (c:Cause {id: r.id}) SET c.name = r.name "
        "WITH c, r UNWIND r.affects AS dev MATCH (d:DeviceType {id: dev}) MERGE (c)-[:AFFECTS]->(d)",
        rows=sd.CAUSES,
    )
    driver.execute_query(
        "UNWIND $rows AS r MATCH (s:Symptom {id: r.symptom}), (c:Cause {id: r.cause}) "
        "MERGE (s)-[i:INDICATES]->(c) SET i.weight = r.weight",
        rows=[{"symptom": s, "cause": c, "weight": w} for s, c, w in sd.INDICATES],
    )
    driver.execute_query(
        "UNWIND $rows AS r MATCH (c:Cause {id: r.cause}), (a:Action {id: r.action}) "
        "MERGE (c)-[x:RESOLVED_BY]->(a) SET x.success_rate = r.rate",
        rows=[{"cause": c, "action": a, "rate": x} for c, a, x in sd.RESOLVED_BY],
    )


def main() -> None:
    s = get_settings()
    uri = s.neo4j_uri or "bolt://localhost:7687"
    with GraphDatabase.driver(uri, auth=(s.neo4j_user, s.neo4j_password)) as driver:
        driver.verify_connectivity()
        seed(driver)
        records, _, _ = driver.execute_query("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label")
        for r in records:
            print(f"{r['label']:<12} {r['n']}")
    print("Seeded.")


if __name__ == "__main__":
    main()
