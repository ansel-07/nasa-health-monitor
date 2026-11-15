# AI-assisted: generated with Claude Code and reviewed by Javi.
"""Practice runs (tutorials, AGENTS.md 16.4): same engine, nothing saved (#97).

Runs the _example fixture protocol with real storage pointed at a temp folder;
only paths and the mission clock are replaced.
"""
from datetime import datetime

import pytest

from core import activity, config, data, mission, models
from core import protocol_engine as engine


@pytest.fixture
def storage(tmp_path, monkeypatch):
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE", "ACTIVITY_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    monkeypatch.setattr(models, "DATA_DIR", tmp_path)
    monkeypatch.setattr(mission, "now", lambda: datetime(2027, 4, 10, 8))
    return tmp_path


@pytest.fixture
def practice():
    return {"id": "practice-_example", "practice": True, "astronaut": "a1", "problem": "_example",
            "environment": "mars", "status": "active", "severity": "moderate",
            "severity_initial": "moderate", "current_node": None, "vars": {}, "answers": {}, "log": []}


def test_full_practice_run_writes_no_files(storage, practice):
    episode = engine.submit(practice, None)
    assert episode["current_node"] == "intro_mars"
    for response in ({"action": "continue"}, {"answer": "no"}, {"action": "done"}, {"value": 25}):
        episode = engine.submit(episode, response)
    # value 25 > 20: escalate, then the flight surgeon contact.
    assert (episode["current_node"], episode["severity"]) == ("contact_now", "severe")
    assert episode["vars"] == {"value_after": 25}
    episode = engine.submit(episode, {"action": "continue"})
    assert (episode["status"], episode["outcome"]) == ("handed_over", "handed_over")
    assert list(storage.iterdir()) == []


def test_practice_does_not_enforce_action_wait(storage, practice):
    practice["current_node"] = "do_action"
    assert engine.current_step(practice)["remaining_wait_min"] == 0
    assert engine.submit(practice, {"action": "done"})["current_node"] == "remeasure"
    assert list(storage.iterdir()) == []


def test_practice_input_is_not_mutated(storage, practice):
    engine.submit(practice, None)
    assert practice["current_node"] is None and practice["log"] == []


def test_practice_symptom_decisions_use_its_readings_across_reruns(storage, monkeypatch):
    problems = {"synthetic": {"symptoms": {"signal": {"levels": [
        {"level": "concern", "when": {"indicator": "_example_indicator", "at_least": 10}},
    ]}}, "states": [{"state": "watch", "when": {"symptom": "signal", "level_is": "concern"}}]}}
    condition = {"symptom": "signal", "level_is": "concern"}
    protocol = {"start": "measure", "nodes": {
        "measure": {"type": "measure", "indicator": "_example_indicator", "save_as": "after", "next": "first"},
        "first": {"type": "decision", "branches": [{"if": condition, "next": "pause"}], "default": "ignored"},
        "pause": {"type": "info", "text": "Synthetic pause.", "next": "second"},
        "second": {"type": "decision", "branches": [{"if": condition, "next": "used"}], "default": "ignored"},
        "ignored": {"type": "end", "outcome": "monitoring", "text": "Synthetic reading ignored."},
        "used": {"type": "end", "outcome": "resolved", "text": "Synthetic reading used."},
    }}
    stored = {"_example_indicator": 1}
    monkeypatch.setattr(data, "latest_values", lambda _: dict(stored))
    monkeypatch.setattr(config, "load_problems", lambda **kwargs: problems)
    monkeypatch.setattr(engine, "load_problems", lambda **kwargs: problems)
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode = engine.practice_episode("a1", "synthetic", "mars")
    episode = engine.submit(episode, {"value": 25})
    assert episode["current_node"] == "pause" and episode["status"] == "active"
    episode = engine.submit(episode, None)
    episode = engine.submit(episode, {"action": "continue"})
    assert episode["current_node"] == "used" and episode["status"] == "resolved"
    assert stored == {"_example_indicator": 1}
    assert list(storage.iterdir()) == []


@pytest.mark.parametrize("level,allowed", [(100, False), (80, False), (70, True), (0, True)])
def test_tutorial_gate(monkeypatch, level, allowed):
    monkeypatch.setattr(activity, "bar_level", lambda astronaut, kind, activity_id: level)
    assert activity.can_repeat_tutorial("a1", "_example") is allowed


def test_practice_episode_runs_real_protocols_without_files(storage):
    episode = engine.practice_episode("a1", "sans", "mars")
    assert episode["practice"] and episode["status"] == "active" and episode["severity"] == "watch"
    assert engine.practice_episode("a1", "_example", "mars")["severity"] == "mild"   # legacy triggers win
    episode = engine.submit(episode, None)
    assert engine.current_step(episode)["type"] in ("info", "action", "measure", "question", "contact")
    assert list(storage.iterdir()) == []
