from app.workflow import run


def path(result):
    return [t["node"] for t in result["trace"]]


def test_ont_no_internet_recommends_fiber_fix(workflow):
    result = run(workflow, "ont", "Customer has no internet and the ONT shows a red LOS light")
    assert result["status"] == "ok"
    assert result["recommendation"]["cause_id"] == "fiber_damage"
    assert len(result["alternatives"]) <= 2
    assert "fiber" in result["explanation"].lower()
    assert path(result) == ["triage_agent", "graph_retrieval_agent", "planner_agent", "reviewer_agent"]


def test_vague_note_asks_for_clarification(workflow):
    result = run(workflow, "router", "Something is weird with it")
    assert result["status"] == "needs_clarification"
    assert result["recommendation"] is None
    assert path(result) == ["triage_agent", "clarify"]


def test_no_known_fix_escalates(workflow):
    result = run(workflow, "small_cell", "Red LOS light on the radio")
    assert result["status"] == "escalated"
    assert path(result) == ["triage_agent", "graph_retrieval_agent", "escalate"]


def test_reviewer_escalates_fixes_that_need_noc(workflow):
    result = run(workflow, "small_cell", "Users report slow speeds and buffering")
    assert result["recommendation"]["action_id"] == "reroute_backhaul"
    assert result["status"] == "escalated"


def test_second_identical_request_hits_cache(workflow):
    first = run(workflow, "router", "Wi-Fi drops and speeds are slow")
    second = run(workflow, "router", "wifi keeps dropping, really slow speeds")
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["recommendation"]["action_id"] == second["recommendation"]["action_id"]


def test_every_node_records_timing(workflow):
    result = run(workflow, "ont", "no power at all, no lights")
    assert result["recommendation"]["action_id"] == "replace_power_adapter"
    assert all(isinstance(t["ms"], float) for t in result["trace"])


class FakeLLM:
    """Stands in for ChatOpenAI so we can test the LLM path without a key."""

    def __init__(self, replies):
        self.replies = list(replies)

    def invoke(self, prompt):
        class Msg:
            content = self.replies.pop(0)
        return Msg()


def test_llm_path_is_used_when_available(store, cache):
    from app.config import get_settings
    from app.workflow import build_workflow

    llm = FakeLLM(['{"symptoms": ["overheating"], "confidence": 0.9}', "Clear the vents first."])
    wf = build_workflow(store, cache, llm=llm, settings=get_settings())
    result = run(wf, "router", "the box is burning up")
    assert result["trace"][0]["method"] == "llm"
    assert result["recommendation"]["action_id"] == "improve_ventilation"
    assert result["explanation"] == "Clear the vents first."


def test_bad_llm_output_falls_back_to_keywords(store, cache):
    from app.config import get_settings
    from app.workflow import build_workflow

    llm = FakeLLM(["sorry, I can't help", "not json either"])
    wf = build_workflow(store, cache, llm=llm, settings=get_settings())
    result = run(wf, "ont", "no power, device is dead")
    assert result["trace"][0]["method"] == "keywords"
    assert result["recommendation"]["action_id"] == "replace_power_adapter"


def test_llm_cannot_invent_symptom_ids(store, cache):
    from app.config import get_settings
    from app.workflow import build_workflow

    llm = FakeLLM(['{"symptoms": ["alien_attack"], "confidence": 0.99}'])
    wf = build_workflow(store, cache, llm=llm, settings=get_settings())
    result = run(wf, "router", "aliens took the router")
    assert result["status"] == "needs_clarification"
