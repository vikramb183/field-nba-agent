"""Settings read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str | None
    neo4j_user: str
    neo4j_password: str
    redis_url: str | None
    openai_api_key: str | None
    llm_model: str
    cache_ttl_seconds: int
    min_triage_confidence: float
    low_score_threshold: float


def get_settings() -> Settings:
    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI") or None,
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "localpassword"),
        redis_url=os.getenv("REDIS_URL") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")),
        min_triage_confidence=float(os.getenv("MIN_TRIAGE_CONFIDENCE", "0.35")),
        low_score_threshold=float(os.getenv("LOW_SCORE_THRESHOLD", "0.25")),
    )
