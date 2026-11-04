"""Wires the agents into a LangGraph StateGraph."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import AgentState, make_agents, route_after_retrieval, route_after_triage
from app.cache import Cache
from app.config import Settings, get_settings
from app.graph_store import GraphStore


def build_workflow(store: GraphStore, cache: Cache, llm=None, settings: Settings | None = None):
    settings = settings or get_settings()
    agents = make_agents(store, cache, settings, llm)

    graph = StateGraph(AgentState)
    for name, fn in agents.items():
        graph.add_node(name, fn)

    graph.add_edge(START, "triage_agent")
    graph.add_conditional_edges(
        "triage_agent",
        route_after_triage(settings.min_triage_confidence),
        {"clarify": "clarify", "graph_retrieval_agent": "graph_retrieval_agent"},
    )
    graph.add_conditional_edges(
        "graph_retrieval_agent",
        route_after_retrieval,
        {"planner_agent": "planner_agent", "escalate": "escalate"},
    )
    graph.add_edge("planner_agent", "reviewer_agent")
    graph.add_edge("reviewer_agent", END)
    graph.add_edge("clarify", END)
    graph.add_edge("escalate", END)

    return graph.compile()


def run(workflow, device_type: str, description: str) -> dict:
    return workflow.invoke({"device_type": device_type, "description": description, "trace": []})
