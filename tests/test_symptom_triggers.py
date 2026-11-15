# AI-assisted: generated with Codex and reviewed by Juan Carlos.
"""Synthetic symptom/state rules; no medical content."""
from copy import deepcopy

import pytest

from core import config, data, triggers


@pytest.fixture
def symptom_setup(monkeypatch):
    problem = {"symptoms": {
        "a": {"levels": [
            {"level": "concern", "when": {"indicator": "x", "above": 15}},
            {"level": "watch", "when": {"indicator": "x", "above": 5}}]},
        "b": {"levels": [
            {"level": "concern", "when": {"indicator": "y", "above": 25}},
            {"level": "watch", "when": {"indicator": "y", "above": 5}}]},
    }, "states": [
        {"state": "medical_urgency", "when": {"count_at_least": 2, "of": [
            {"symptom": "a", "level_is": "concern"}, {"symptom": "b", "level_is": "concern"}]}},
        {"state": "watch", "when": {"any": [
            {"symptom": "a", "level_at_least": "watch"}, {"symptom": "b", "level_at_least": "watch"}]}},
    ]}
    problems = {"test_problem": problem}
    latest = {"x": 0, "y": 30}
    monkeypatch.setattr(config, "load_problems", lambda include_examples=False: problems)
    monkeypatch.setattr(data, "latest_values", lambda astronaut: latest)
    monkeypatch.setattr(data, "z_score", lambda *args: None)
    return problems, latest, {"astronaut": "a1", "indicator": "x", "value": 20}


def test_new_measurement_overrides_latest_and_calculates_state(symptom_setup):
    problems, latest, m = symptom_setup
    before = deepcopy((problems, latest))
    assert triggers.evaluate(m, "mars") == [{"problem": "test_problem", "severity": "medical_urgency",
        "indicator": "x", "value": 20, "z": None, "symptoms": {"a": "concern", "b": "concern"}}]
    assert (problems, latest) == before
    assert triggers.symptom_levels("test_problem", "a1", "mars") == {"a": "not_present", "b": "concern"}


def test_normal_incoming_value_does_not_raise_another_symptoms_alert(symptom_setup):
    _, latest, m = symptom_setup
    m["value"] = 0
    assert latest["y"] == 30
    assert triggers.evaluate(m, "mars") == []
    assert triggers.symptom_levels("test_problem", "a1", "mars")["b"] == "concern"


def test_first_matching_level_and_state_win(symptom_setup):
    problems, latest, m = symptom_setup
    problem = problems["test_problem"]
    problem["symptoms"]["a"]["levels"].reverse()
    result = triggers.evaluate(m, "mars")[0]
    assert result["symptoms"]["a"] == "watch"
    assert result["severity"] == "watch"
    problem["symptoms"]["a"]["levels"].reverse()
    problem["states"].reverse()
    assert triggers.evaluate(m, "mars")[0]["severity"] == "watch"


@pytest.mark.parametrize("initially_missing", [False, True])
def test_baseline_lookup_is_shared_only_within_one_evaluation(symptom_setup, monkeypatch, initially_missing):
    problems, _, m = symptom_setup
    problems["test_problem"]["symptoms"]["a"]["levels"] = [
        {"level": "concern", "when": {"indicator": "x", "metric": "baseline_fraction", "above": 2.5}},
        {"level": "watch", "when": {"indicator": "x", "metric": "baseline_fraction", "above": 1.5}},
    ]
    baseline = [None if initially_missing else {"mean": 10, "std": 1, "n": 2}]
    calls = []

    def lookup(astronaut, indicator):
        calls.append((astronaut, indicator))
        return baseline[0]

    monkeypatch.setattr(data, "get_baseline", lookup)
    result = triggers.evaluate(m, "mars")
    assert bool(result) is not initially_missing
    if result:
        assert result[0]["symptoms"]["a"] == "watch"
    assert calls == [("a1", "x")]
    baseline[0] = {"mean": 10 if initially_missing else 20, "std": 1, "n": 2}
    assert bool(triggers.evaluate(m, "mars")) is initially_missing
    assert calls == [("a1", "x"), ("a1", "x")]


def test_environment_missing_values_and_unrelated_indicators(symptom_setup):
    problems, latest, m = symptom_setup
    problems["test_problem"]["symptoms"]["a"]["levels"][0]["environments"] = ["mars"]
    assert triggers.evaluate(m, "iss")[0]["symptoms"]["a"] == "watch"
    latest.clear()
    m["value"] = 0
    assert triggers.evaluate(m, "mars") == []
    m.update(indicator="unrelated", value=100)
    assert triggers.evaluate(m, "mars") == []


def test_new_format_wins_over_legacy_but_legacy_problems_still_work(symptom_setup):
    problems, _, m = symptom_setup
    legacy = {"triggers": [{"severity": "mild", "when": {"indicator": "x", "above": 1}}]}
    problems["legacy"] = legacy
    problems["test_problem"].update(legacy)
    problems["_hidden"] = deepcopy(problems["test_problem"])
    results = triggers.evaluate(m, "mars")
    assert [item["severity"] for item in results] == ["medical_urgency", "mild"]


@pytest.mark.parametrize("change", ["missing_states", "unknown_symptom", "indicator_in_state", "symptom_in_level", "bad_level", "bad_count"])
def test_invalid_symptom_configuration_is_explicit(symptom_setup, change):
    problems, _, m = symptom_setup
    problem = problems["test_problem"]
    if change == "missing_states":
        del problem["states"]
    elif change == "unknown_symptom":
        problem["states"][0]["when"] = {"symptom": "unknown", "level_is": "watch"}
    elif change == "indicator_in_state":
        problem["states"][0]["when"] = {"indicator": "x", "above": 1}
    elif change == "symptom_in_level":
        problem["symptoms"]["a"]["levels"][0]["when"] = {"symptom": "b", "level_is": "watch"}
    elif change == "bad_level":
        problem["symptoms"]["a"]["levels"][0]["level"] = "severe"
    else:
        problem["states"][0]["when"]["count_at_least"] = 0
    with pytest.raises(ValueError, match="Problem 'test_problem'"):
        triggers.evaluate(m, "mars")
