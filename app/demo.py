"""Run a few example tickets through the agent from the command line.

Usage:  python -m app.demo
"""
from __future__ import annotations

from app.cache import InMemoryCache
from app.config import get_settings
from app.graph_store import InMemoryGraphStore
from app.llm import get_llm
from app.workflow import build_workflow, run

EXAMPLES = [
    ("ont", "Customer has no internet and the ONT shows a red LOS light"),
    ("router", "Wi-Fi drops every few minutes upstairs and speeds are slow"),
    ("small_cell", "Users near the tower report slow speeds and buffering"),
    ("router", "Something is weird with it"),
]


def main() -> None:
    settings = get_settings()
    workflow = build_workflow(InMemoryGraphStore(), InMemoryCache(), get_llm(settings), settings)
    for device, note in EXAMPLES:
        result = run(workflow, device, note)
        print(f"\n[{device}] {note}")
        print(f"  status: {result['status']}  symptoms: {result.get('symptoms')}")
        if result.get("recommendation"):
            print(f"  next action: {result['recommendation']['action']}")
            print(f"  why: {result['explanation']}")
        else:
            print(f"  message: {result['message']}")
        for w in result.get("warnings", []):
            print(f"  warning: {w}")
        print("  path: " + " -> ".join(t["node"] for t in result["trace"]))

    print("\nWorkflow graph (paste into https://mermaid.live):\n")
    print(workflow.get_graph().draw_mermaid())


if __name__ == "__main__":
    main()
