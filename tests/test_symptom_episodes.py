# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Symptom-based episode lifecycle using synthetic content and temporary storage."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from core import config, data, episodes, mission, models


@pytest.fixture
def symptom_state(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    metadata = {key: {"name": key, "unit": "example"} for key in ("x", "y")}
    monkeypatch.setattr(data, "load_indicators", lambda: metadata)
    monkeypatch.setattr(config, "load_indicators", lambda: metadata)
    clock = [datetime(2027, 4, 10, 8)]
    monkeypatch.setattr(mission, "now", lambda: clock[0])
    problem = {"confirm_wait_min": 5, "symptoms": {
        sid: {"name": sid, "levels": [
            {"level": "concern", "when": {"indicator": indicator, "above": 15}},
            {"level": "watch", "when": {"indicator": indicator, "above": 5}},
        ]} for sid, indicator in (("a", "x"), ("b", "y"))
    }, "states": [
        {"state": "medical_urgency", "when": {"count_at_least": 2, "of": [
            {"symptom": "a", "level_is": "concern"}, {"symptom": "b", "level_is": "concern"}]}},
        {"state": "watch", "when": {"count_at_least": 1, "of": [
            {"symptom": "a", "level_at_least": "watch"}, {"symptom": "b", "level_at_least": "watch"}]}},
    ]}
    problems = {"synthetic": problem}
    monkeypatch.setattr(config, "load_problems", lambda include_examples=False: problems)
    monkeypatch.setattr(config, "load_protocol", lambda problem_id: {"start": "first"})
    data.add_measurement(measurement(clock, indicator="y", value=0))
    return clock, problems


def measurement(clock, **changes):
    return {"timestamp": clock[0].isoformat(), "astronaut": "a1", "indicator": "x", "value": 20,
            "unit": "example", "phase": "mission", "source": "manual", **changes}


@pytest.mark.parametrize("repeat_value,status", [(20, "active"), (10, "active"), (0, "dismissed")])
def test_symptom_episode_opens_and_requires_repeat(symptom_state, repeat_value, status):
    clock, _ = symptom_state
    initial = episodes.on_new_measurement(measurement(clock), "mars")
    assert initial["severity"] == "watch"
    assert initial["symptoms"] == {"a": "concern", "b": "not_present"}
    clock[0] += timedelta(minutes=5)
    result = episodes.confirm(initial["id"], measurement(clock, value=repeat_value))
    assert result["status"] == status
    assert result["severity_initial"] == "watch"
    assert data.load_episodes() == [result]
    if status == "active":
        assert result["symptoms"]["a"] == ("concern" if repeat_value == 20 else "watch")


def test_other_indicator_updates_state_only_during_explicit_confirmation(symptom_state):
    clock, _ = symptom_state
    initial = episodes.on_new_measurement(measurement(clock), "mars")
    clock[0] += timedelta(minutes=1)
    assert episodes.on_new_measurement(measurement(clock, indicator="y"), "mars") == initial
    clock[0] += timedelta(minutes=4)
    result = episodes.confirm(initial["id"], measurement(clock))
    assert result["severity"] == "medical_urgency"
    assert result["severity_initial"] == "watch"
    assert result["symptoms"] == {"a": "concern", "b": "concern"}


def test_symptom_pending_survives_closure_and_restarts_confirmation(symptom_state):
    clock, problems = symptom_state
    problems["second"] = deepcopy(problems["synthetic"])
    first = episodes.on_new_measurement(measurement(clock), "mars")
    queued = episodes.get_pending("a1")[0]
    assert queued["severity"] == "watch" and queued["symptoms"]["a"] == "concern"
    data.save_episode({**first, "status": "resolved", "outcome": "resolved", "closed_at": clock[0].isoformat()})
    clock[0] += timedelta(minutes=1)
    next_episode = episodes.accept_pending("a1", "iss")
    assert next_episode["problem"] == "second"
    assert next_episode["opened_at"] == clock[0].isoformat()
    assert next_episode["symptoms"] == queued["symptoms"]
    with pytest.raises(ValueError, match="confirm_wait_min"):
        episodes.confirm(next_episode["id"], measurement(clock))
    clock[0] += timedelta(minutes=5)
    assert episodes.confirm(next_episode["id"], measurement(clock))["status"] == "active"


def test_mixed_queue_transition_priority_is_stable(symptom_state):
    entries = [{"astronaut": "a1", "problem": str(index), "severity": severity}
               for index, severity in enumerate(("watch", "moderate", "medical_urgency", "mild", "severe"))]
    data.save_pending(entries)
    assert [item["severity"] for item in episodes.get_pending("a1")] == [
        "medical_urgency", "severe", "moderate", "watch", "mild"]


def test_unknown_symptom_data_cannot_silently_dismiss(symptom_state):
    clock, _ = symptom_state
    initial = episodes.on_new_measurement(measurement(clock), "mars")
    rows = data.load_measurements()
    rows[rows["indicator"] != "y"].to_csv(models.MEASUREMENTS_FILE, index=False)
    clock[0] += timedelta(minutes=5)
    with pytest.raises(ValueError, match="unavailable"):
        episodes.confirm(initial["id"], measurement(clock, value=0))
    assert data.get_open_episode("a1") == initial
    assert len(data.load_measurements()) == 1


def test_unknown_baseline_cannot_understate_first_matching_state(symptom_state):
    clock, problems = symptom_state
    initial = episodes.on_new_measurement(measurement(clock, value=10), "mars")
    problem = problems["synthetic"]
    problem["symptoms"]["a"]["levels"].insert(0, {
        "level": "concern", "when": {"indicator": "x", "z_above": 2}})
    problem["states"][0]["when"] = {"symptom": "a", "level_is": "concern"}
    clock[0] += timedelta(minutes=5)
    with pytest.raises(ValueError, match="baseline"):
        episodes.confirm(initial["id"], measurement(clock, value=10))
    assert data.get_open_episode("a1") == initial


def test_unknown_data_is_allowed_when_it_cannot_change_state(symptom_state):
    clock, problems = symptom_state
    initial = episodes.on_new_measurement(measurement(clock), "mars")
    problem = problems["synthetic"]
    problem["states"] = [problem["states"][1]]
    problem["symptoms"]["b"]["levels"][0]["when"] = {"indicator": "y", "z_above": 2}
    clock[0] += timedelta(minutes=5)
    assert episodes.confirm(initial["id"], measurement(clock))["severity"] == "watch"
