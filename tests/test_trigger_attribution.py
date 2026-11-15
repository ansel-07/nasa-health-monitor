# AI-assisted: generated with Codex and reviewed by Juan Carlos.
"""Synthetic batch attribution: matched states never substitute incoming evidence."""
import json
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from core import config, data, episodes, mission, models, triggers


START = datetime(2027, 4, 10, 8)
INDICATORS = ["normal_first", "eye_left", "eye_right"] + [f"other_{i}" for i in range(11)]


@pytest.fixture
def batch(tmp_path, monkeypatch):
    folder = tmp_path / "config"
    folder.mkdir()
    monkeypatch.setattr(config, "CONFIG_DIR", folder)
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE", "ASTRONAUTS_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    models.ASTRONAUTS_FILE.write_text("id,name,role\na1,A,Test\na2,B,Test\na3,C,Test\n", encoding="utf-8")
    problem = {"name": "Synthetic problem", "confirm_wait_min": 5, "protocol": "protocol.json",
        "symptoms": {key: {"levels": [{"level": "watch", "when": {"indicator": key, "above": 10}}]}
                     for key in INDICATORS},
        "states": [{"state": "watch", "when": {"count_at_least": 1, "of": [
            {"symptom": key, "level_is": "watch"} for key in INDICATORS]}}]}
    problems = {"first": problem, "second": deepcopy(problem)}
    for filename, value in {
        "mission.json": {"start": START.isoformat()},
        "indicators.json": {key: {"unit": "synthetic"} for key in INDICATORS},
        "problems.json": problems,
        "protocol.json": {"problem": "first", "start": "intro", "nodes": {
            "intro": {"type": "info", "text": "Synthetic fixture.", "next": "end"},
            "end": {"type": "end", "text": "Synthetic fixture.", "outcome": "resolved"}}},
    }.items():
        (folder / filename).write_text(json.dumps(value), encoding="utf-8")
    return folder, problems


def reading(indicator, value, timestamp, astronaut="a1", source="simulated"):
    return {"timestamp": timestamp.isoformat(), "astronaut": astronaut, "indicator": indicator,
            "value": value, "unit": "synthetic", "phase": "mission", "source": source}


@pytest.mark.parametrize("abnormal", ["eye_left", "eye_right"])
@pytest.mark.parametrize("reverse", [False, True])
def test_fourteen_indicator_batches_preserve_eye_evidence_and_one_open_episode(batch, abnormal, reverse):
    order = list(reversed(INDICATORS)) if reverse else INDICATORS
    for astronaut in ("a1", "a2", "a3"):
        for indicator in order:
            data.add_measurement(reading(indicator, 20 if astronaut == "a1" and indicator == abnormal else 0,
                                         START + timedelta(minutes=30), astronaut))
    result = mission.advance_and_detect(1, "mars")
    assert (result["revealed"], result["new_alerts"]) == (42, ["a1"])
    opened = data.get_open_episode("a1")
    assert opened["trigger"]["indicator"] == abnormal and opened["trigger"]["value"] == 20
    pending = episodes.get_pending("a1")
    assert len(pending) == 1
    assert pending[0]["indicator"] == abnormal and pending[0]["value"] == 20
    assert data.load_episodes("a2") == [] and data.load_episodes("a3") == []

    # A later normal batch cannot replace the queued positive evidence.
    for astronaut in ("a1", "a2", "a3"):
        for indicator in order:
            data.add_measurement(reading(indicator, 20 if astronaut == "a2" and indicator == abnormal else 0,
                                         START + timedelta(minutes=90), astronaut))
    result = mission.advance_and_detect(1, "mars")
    assert (result["revealed"], result["new_alerts"]) == (42, ["a2"])
    assert data.get_open_episode("a1") == opened
    assert episodes.get_pending("a1") == pending
    assert data.get_open_episode("a2")["trigger"]["indicator"] == abnormal
    assert len(data.load_episodes("a1")) == 1
    wrong = "eye_right" if abnormal == "eye_left" else "eye_left"
    with pytest.raises(ValueError, match="same indicator"):
        episodes.confirm(opened["id"], reading(wrong, 20, mission.now(), source="manual"))
    active = episodes.confirm(opened["id"], reading(abnormal, 20, mission.now(), source="manual"))
    assert active["status"] == "active" and active["trigger"]["indicator"] == abnormal
    assert len(data.load_measurements()) == 85  # 84 stored simulated rows plus one repeat.


@pytest.mark.parametrize("condition", [
    {"any": [{"indicator": "eye_left", "above": 10}, {"indicator": "eye_right", "above": 10}]},
    {"any": [{"all": [{"indicator": "eye_left", "below": 5},
                        {"indicator": "eye_right", "above": 100}]},
             {"indicator": "eye_right", "above": 10}]},
    {"count_at_least": 2, "of": [{"indicator": "eye_left", "above": 10},
        {"indicator": "eye_right", "above": 10}, {"environment_in": ["mars"]}]},
])
def test_false_or_irrelevant_branches_do_not_supply_episode_evidence(batch, condition):
    folder, problems = batch
    for problem in problems.values():
        problem["symptoms"] = {"combined": {"levels": [{"level": "watch", "when": condition}]}}
        problem["states"] = [{"state": "watch", "when": {"symptom": "combined", "level_is": "watch"}}]
    (folder / "problems.json").write_text(json.dumps(problems), encoding="utf-8")
    data.add_measurement(reading("eye_right", 20, START))
    normal = reading("eye_left", 0, START, source="manual")
    assert triggers.symptom_levels("first", "a1", "mars")["combined"] == "watch"
    assert triggers.evaluate(normal, "mars") == []  # State and alert attribution are distinct.
    assert episodes.on_new_measurement(normal, "mars") is None
    assert data.load_pending() == []
    assert episodes.on_new_measurement(reading("eye_right", 20, START, source="manual"), "mars")["trigger"]["indicator"] == "eye_right"


def test_first_matching_level_supplies_evidence_and_state_uses_all_latest_symptoms(batch):
    folder, problems = batch
    problem = problems["first"]
    problem["symptoms"] = {
        "a": {"levels": [{"level": "concern", "when": {"indicator": "eye_right", "above": 10}},
                         {"level": "watch", "when": {"indicator": "eye_left", "above": 10}}]},
        "b": {"levels": [{"level": "watch", "when": {"indicator": "normal_first", "above": 10}}]},
    }
    problem["states"] = [
        {"state": "medical_urgency", "when": {"symptom": "a", "level_is": "concern"}},
        {"state": "watch", "when": {"symptom": "b", "level_is": "watch"}},
    ]
    (folder / "problems.json").write_text(json.dumps({"first": problem}), encoding="utf-8")
    for indicator in ("eye_right", "eye_left", "normal_first"):
        data.add_measurement(reading(indicator, 20, START))
    assert episodes.on_new_measurement(reading("eye_left", 20, START), "mars") is None
    result = triggers.evaluate(reading("normal_first", 20, START), "mars")[0]
    assert result["severity"] == "medical_urgency"  # Positive b uses the full state, not its own level.
    opened = episodes.on_new_measurement(reading("eye_right", 20, START), "mars")
    assert opened["severity"] == "medical_urgency" and opened["trigger"]["indicator"] == "eye_right"


def test_count_state_accepts_either_positive_indicator_but_not_a_normal_one(batch):
    folder, problems = batch
    problem = problems["first"]
    problem["states"] = [{"state": "watch", "when": {"count_at_least": 2, "of": [
        {"symptom": "eye_left", "level_is": "watch"},
        {"symptom": "eye_right", "level_is": "watch"}]}}]
    (folder / "problems.json").write_text(json.dumps({"first": problem}), encoding="utf-8")
    for indicator in ("eye_left", "eye_right"):
        data.add_measurement(reading(indicator, 20, START))
    assert episodes.on_new_measurement(reading("normal_first", 0, START), "mars") is None
    for indicator in ("eye_left", "eye_right"):
        m = reading(indicator, 20, START)
        assert triggers.evaluate(m, "mars")[0]["indicator"] == indicator
    opened = episodes.on_new_measurement(reading("eye_right", 20, START), "mars")
    assert opened["trigger"]["indicator"] == "eye_right"


def test_confirmation_does_not_queue_an_unrelated_positive_symptom_as_repeat_evidence(batch):
    folder, problems = batch
    problems["first"]["states"] = [{"state": "watch", "when": {"symptom": "eye_left", "level_is": "watch"}}]
    problems["second"]["states"] = [{"state": "watch", "when": {"symptom": "eye_right", "level_is": "watch"}}]
    problems["second"]["symptoms"]["eye_left"]["levels"] = [
        {"level": "watch", "when": {"indicator": "eye_left", "above": 100}}]
    (folder / "problems.json").write_text(json.dumps(problems), encoding="utf-8")
    opened = episodes.on_new_measurement(reading("eye_left", 20, START, source="manual"), "mars")
    assert data.load_pending() == []
    mission.advance(1)
    data.add_measurement(reading("eye_right", 20, mission.now(), source="manual"))
    assert episodes.confirm(opened["id"], reading("eye_left", 20, mission.now(), source="manual"))["status"] == "active"
    assert data.load_pending() == []


def test_legacy_any_keeps_its_existing_alert_contract(batch):
    folder, _ = batch
    problem = {"name": "Legacy fixture", "confirm_wait_min": 5, "triggers": [{
        "severity": "mild", "when": {"any": [{"indicator": "eye_left", "above": 10},
                                               {"indicator": "eye_right", "above": 10}]}}]}
    (folder / "problems.json").write_text(json.dumps({"first": problem}), encoding="utf-8")
    data.add_measurement(reading("eye_right", 20, START))
    normal = reading("eye_left", 0, START, source="manual")
    assert triggers.evaluate(normal, "mars")[0]["indicator"] == "eye_left"
    assert episodes.on_new_measurement(normal, "mars")["trigger"]["indicator"] == "eye_left"
