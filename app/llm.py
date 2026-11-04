"""LLM helpers with deterministic fallbacks.

With OPENAI_API_KEY set, the triage and planner agents use an LLM through
LangChain. Without it, they fall back to keyword matching and a template, so
the project runs and tests offline.
"""
from __future__ import annotations

import json
import re

from app.config import Settings


def get_llm(settings: Settings):
    if not settings.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=settings.llm_model, temperature=0, api_key=settings.openai_api_key)


def _mentions(text: str, keyword: str) -> bool:
    # Whole-word match with simple plural/tense endings, so "los" matches "LOS" but not "lost".
    return re.search(rf"\b{re.escape(keyword)}(s|es|ed|ing)?\b", text) is not None


def keyword_triage(description: str, symptoms: list[dict]) -> tuple[list[str], float]:
    text = description.lower()
    matched = [s["id"] for s in symptoms if any(_mentions(text, k) for k in s["keywords"])]
    if not matched:
        return [], 0.0
    confidence = min(0.95, 0.7 + 0.1 * (len(matched) - 1))
    return matched, round(confidence, 2)


def llm_triage(llm, description: str, symptoms: list[dict]) -> tuple[list[str], float]:
    options = "\n".join(f"- {s['id']}: {s['name']}" for s in symptoms)
    prompt = (
        "You are a field-service triage assistant. Map the technician's note to symptom ids.\n"
        f"Allowed symptom ids:\n{options}\n\n"
        f"Technician note: {description!r}\n\n"
        'Reply with JSON only: {"symptoms": [ids], "confidence": number between 0 and 1}. '
        "Use only allowed ids. Use an empty list if none apply."
    )
    reply = llm.invoke(prompt).content
    match = re.search(r"\{.*\}", reply, re.S)
    if not match:
        raise ValueError("LLM reply had no JSON")
    data = json.loads(match.group(0))
    allowed = {s["id"] for s in symptoms}
    ids = [i for i in data.get("symptoms", []) if i in allowed]
    confidence = max(0.0, min(1.0, float(data.get("confidence", 0))))
    return ids, round(confidence, 2)


def template_explanation(top: dict, alternatives: list[dict]) -> str:
    text = (
        f"Most likely cause: {top['cause']}. "
        f"Start with \"{top['action']}\" (about {top['est_minutes']} min, "
        f"{round(top['success_rate'] * 100)}% historical fix rate)."
    )
    if alternatives:
        text += f" If that doesn't work, try \"{alternatives[0]['action']}\"."
    return text


def llm_explanation(llm, description: str, top: dict, alternatives: list[dict]) -> str:
    prompt = (
        "Write 2 short sentences for a field technician explaining the recommended next action. "
        "Use only the facts given. Do not invent steps.\n"
        f"Technician note: {description!r}\n"
        f"Recommended: {json.dumps(top)}\n"
        f"Alternatives: {json.dumps(alternatives)}"
    )
    return llm.invoke(prompt).content.strip()
