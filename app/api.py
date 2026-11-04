"""FastAPI service: POST /next-best-action."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.cache import InMemoryCache, RedisCache
from app.config import get_settings
from app.graph_store import InMemoryGraphStore, Neo4jGraphStore
from app.llm import get_llm
from app.workflow import build_workflow, run

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("field-nba-agent")


class NBARequest(BaseModel):
    device_type: Literal["ont", "router", "small_cell"]
    description: str = Field(min_length=3, max_length=1000,
                             examples=["Customer has no internet and the ONT shows a red LOS light"])


class NBAResponse(BaseModel):
    status: str
    message: str
    symptoms: list[str] = []
    confidence: float = 0.0
    recommendation: dict | None = None
    alternatives: list[dict] = []
    explanation: str | None = None
    warnings: list[str] = []
    cache_hit: bool = False
    trace: list[dict] = []


def create_app(store=None, cache=None, llm=None) -> FastAPI:
    settings = get_settings()
    if store is None:
        store = (Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
                 if settings.neo4j_uri else InMemoryGraphStore())
    if cache is None:
        cache = RedisCache(settings.redis_url) if settings.redis_url else InMemoryCache()
    if llm is None:
        llm = get_llm(settings)

    log.info("store=%s cache=%s llm=%s", type(store).__name__, type(cache).__name__,
             type(llm).__name__ if llm else "none (keyword fallback)")
    workflow = build_workflow(store, cache, llm, settings)

    app = FastAPI(title="Field Next-Best-Action Agent", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "store": type(store).__name__, "cache": type(cache).__name__,
                "llm": bool(llm)}

    @app.get("/workflow")
    def workflow_diagram():
        return {"mermaid": workflow.get_graph().draw_mermaid()}

    @app.post("/next-best-action", response_model=NBAResponse)
    def next_best_action(req: NBARequest):
        result = run(workflow, req.device_type, req.description)
        log.info("nba device=%s status=%s trace=%s", req.device_type, result.get("status"),
                 [(t["node"], t["ms"]) for t in result.get("trace", [])])
        return NBAResponse(**{k: v for k, v in result.items() if k in NBAResponse.model_fields})

    return app

