from app import sample_data as sd
from app.llm import keyword_triage


def test_finds_multiple_symptoms():
    ids, confidence = keyword_triage("Red LOS light and no internet since this morning", sd.SYMPTOMS)
    assert set(ids) == {"los_light", "no_internet"}
    assert confidence > 0.7


def test_word_boundaries_avoid_false_matches():
    # "lost" must not trigger the LOS-light symptom
    ids, _ = keyword_triage("Customer lost the remote", sd.SYMPTOMS)
    assert "los_light" not in ids


def test_handles_plurals_and_tenses():
    ids, _ = keyword_triage("Wi-Fi keeps dropping and speeds are bad", sd.SYMPTOMS)
    assert set(ids) == {"wifi_drops", "slow_speed"}


def test_vague_note_returns_nothing():
    assert keyword_triage("Something is weird with it", sd.SYMPTOMS) == ([], 0.0)
