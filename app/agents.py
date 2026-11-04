"""The four agents (LangGraph nodes) and the routing between them.

triage_agent      -> turns a free-text technician note into symptom ids
graph_retrieval   -> asks the knowledge graph (Neo4j) for candidate fixes, with a cache in front
planner_agent     -> ranks candidates and writes a short explanation
reviewer_agent    -> guardrail: escalates or flags risky / low-confidence answers
"""
from __future__ import annotations

import logging
import operator
import time
from typing import Annotated, Literal, TypedDict

from app import llm as llm_helpers
from app.cache import Cache
from app.config import Settings
from app.graph_store import GraphStore

log = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    device_type: str
    description: str
    symptoms: list[str]
    confidence: float
    candidates: list[dict]
    cache_hit: bool
    recommendation: dict | None
    alternatives: list[dict]
    explanation: str
    status: Literal["ok", "needs_clarification", "escalated"]
    message: str
    warnings: list[str]
    # Each node appends one entry; operator.add tells LangGraph to concatenate.
    trace: Annotated[list[dict], operator.add]


def _trace(node: str, started: float, **extra) -> list[dict]:
    return [{"node": node, "ms": round((time.perf_counter() - started) * 1000, 2), **extra}]


def action_score(c: dict) -> float:
    """Likelihood of the cause x historical fix rate, lightly penalised by time on site."""
    return c["cause_score"] * c["success_rate"] / (1 + c["est_minutes"] / 120)


def cache_key(device_type: str, symptoms: list[str]) -> str:
    return f"nba:{device_type}:{','.join(sorted(symptoms))}"


def make_agents(store: GraphStore, cache: Cache, settings: Settings, llm=None) -> dict:
    symptoms_catalog = store.list_symptoms()

    def triage_agent(state: AgentState) -> dict:
        started = time.perf_counter()
        method = "keywords"
        ids, confidence = [], 0.0
        if llm is not None:
            try:
                ids, confidence = llm_helpers.llm_triage(llm, state["description"], symptoms_catalog)
                method = "llm"
            except Exception as exc:  # fall back rather than fail the request
                log.warning("LLM triage failed, using keywords: %s", exc)
        if method == "keywords":
            ids, confidence = llm_helpers.keyword_triage(state["description"], symptoms_catalog)
        return {
            "symptoms": ids,
            "confidence": confidence,
            "trace": _trace("triage_agent", started, method=method, symptoms=ids, confidence=confidence),
        }

    def clarify(state: AgentState) -> dict:
        started = time.perf_counter()
        names = "; ".join(s["name"] for s in symptoms_catalog)
        return {
            "status": "needs_clarification",
            "message": f"I couldn't tell what's wrong. Can you describe the symptom? For example: {names}.",
            "recommendation": None,
            "alternatives": [],
            "trace": _trace("clarify", started),
        }

    def graph_retrieval_agent(state: AgentState) -> dict:
        started = time.perf_counter()
        key = cache_key(state["device_type"], state["symptoms"])
        cached = cache.get(key)
        if cached is not None:
            return {"candidates": cached, "cache_hit": True,
                    "trace": _trace("graph_retrieval_agent", started, cache_hit=True, candidates=len(cached))}
        candidates = store.find_candidate_actions(state["device_type"], state["symptoms"], limit=5)
        if candidates:
            cache.set(key, candidates, settings.cache_ttl_seconds)
        return {"candidates": candidates, "cache_hit": False,
                "trace": _trace("graph_retrieval_agent", started, cache_hit=False, candidates=len(candidates))}

    def escalate(state: AgentState) -> dict:
        started = time.perf_counter()
        return {
            "status": "escalated",
            "message": "No known fix in the knowledge graph for this device and symptom. Escalating to Tier 2.",
            "recommendation": None,
            "alternatives": [],
            "trace": _trace("escalate", started),
        }

    def planner_agent(state: AgentState) -> dict:
        started = time.perf_counter()
        ranked = sorted(state["candidates"], key=action_score, reverse=True)
        ranked = [{**c, "score": round(action_score(c), 3)} for c in ranked]
        top, alternatives = ranked[0], ranked[1:3]
        explanation = llm_helpers.template_explanation(top, alternatives)
        if llm is not None:
            try:
                explanation = llm_helpers.llm_explanation(llm, state["description"], top, alternatives)
            except Exception as exc:
                log.warning("LLM explanation failed, using template: %s", exc)
        return {
            "recommendation": top,
            "alternatives": alternatives,
            "explanation": explanation,
            "trace": _trace("planner_agent", started, picked=top["action_id"]),
        }

    def reviewer_agent(state: AgentState) -> dict:
        started = time.perf_counter()
        top = state["recommendation"]
        warnings: list[str] = []
        status, message = "ok", "Recommendation ready."
        if top["requires_escalation"]:
            status = "escalated"
            message = "The best fix needs the network operations center. Escalating with the plan attached."
        if top["score"] < settings.low_score_threshold:
            warnings.append("Low confidence in this fix. Verify on site before acting.")
        if state.get("confidence", 1.0) < 0.6:
            warnings.append("Symptom match was partial. Confirm the symptom with the customer.")
        return {"status": status, "message": message, "warnings": warnings,
                "trace": _trace("reviewer_agent", started, status=status, warnings=len(warnings))}

    return {
        "triage_agent": triage_agent,
        "clarify": clarify,
        "graph_retrieval_agent": graph_retrieval_agent,
        "escalate": escalate,
        "planner_agent": planner_agent,
        "reviewer_agent": reviewer_agent,
    }


def route_after_triage(min_confidence: float):
    def _route(state: AgentState) -> str:
        if not state.get("symptoms") or state.get("confidence", 0) < min_confidence:
            return "clarify"
        return "graph_retrieval_agent"
    return _route


def route_after_retrieval(state: AgentState) -> str:
    return "planner_agent" if state.get("candidates") else "escalate"
