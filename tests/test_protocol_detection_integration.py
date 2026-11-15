# AI-assisted: generated with Claude Code and reviewed by Javi.
"""Protocol readings routed through episode detection, with real CSV/JSON storage.

All indicators, rules and protocols are synthetic test fixtures, not health
content. Only paths and the mission clock are replaced; the protocol engine,
episodes, triggers, conditions, config and data run their real implementations.
"""
import json
from datetime import datetime

import pytest

from core import config, data, episodes, mission, models
from core import protocol_engine as engine

SIGNAL = "synthetic_signal"
ORIGIN = "synthetic_origin"
OTHER = "synthetic_other"


@pytest.fixture
def storage(tmp_path, monkeypatch):
    protocols = tmp_path / "config" / "protocols"
    protocols.mkdir(parents=True)
    indicators = {SIGNAL: {"name": SIGNAL, "unit": "test units", "how_to_measure": "Test input.",
                           "why_it_matters": "Synthetic test fixture.", "source": "none"}}
    # Both problems match the same reading, so one protocol reading can detect the other problem.
    problems = {problem: {"name": problem, "confirm_wait_min": 5, "protocol": f"protocols/{problem}.json",
                          "triggers": [{"severity": severity, "when": {"indicator": SIGNAL, "above": 20}}],
                          "source": "none"}
                for problem, severity in ((ORIGIN, "mild"), (OTHER, "moderate"))}
    protocol = {"problem": ORIGIN, "start": "remeasure", "nodes": {
        "remeasure": {"type": "measure", "indicator": SIGNAL, "save_as": "after", "next": "check"},
        "check": {"type": "decision", "default": "explain",
                  "branches": [{"if": {"var": "after", "above": 20}, "next": "handover"}]},
        "handover": {"type": "end", "outcome": "handed_over", "text": "Synthetic handover."},
        "explain": {"type": "info", "text": "Synthetic step.", "next": "done"},
        "done": {"type": "end", "outcome": "resolved", "text": "Synthetic end."}}}
    other_protocol = {"problem": OTHER, "start": "done", "nodes": {
        "done": {"type": "end", "outcome": "resolved", "text": "Synthetic end."}}}
    environments = {"mars": {"name": "Synthetic Mars", "gravity_g": 1, "comm_delay_min": 1, "source": "none"}}
    for path, content in ((tmp_path / "config" / "indicators.json", indicators),
                          (tmp_path / "config" / "environments.json", environments),
                          (tmp_path / "config" / "problems.json", problems),
                          (protocols / f"{ORIGIN}.json", protocol),
                          (protocols / f"{OTHER}.json", other_protocol)):
        path.write_text(json.dumps(content), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(mission, "now", lambda: datetime(2027, 4, 10, 8))
    origin = {"id": "ep-0001", "astronaut": "a1", "problem": ORIGIN, "environment": "mars",
              "status": "active", "severity_initial": "mild", "severity": "mild",
              "trigger": {"indicator": SIGNAL, "value": 30.0, "z": None, "measured_at": "2027-04-10T07:00:00"},
              "current_node": None, "vars": {}, "answers": {}, "log": [],
              "opened_at": "2027-04-10T07:05:00", "closed_at": None, "outcome": None}
    data.save_episode(origin)
    return origin


def protocol_rows():
    rows = data.load_measurements(astronaut="a1", indicator=SIGNAL)
    return rows[rows["source"] == "protocol"].to_dict("records")


def test_reading_detects_other_problem_while_measure_runs_to_end(storage):
    updated = engine.submit(storage, {"value": 25})
    # The protocol's own route wins: the reading ends the origin episode.
    assert (updated["status"], updated["outcome"], updated["severity"]) == ("handed_over", "handed_over", "mild")
    # The origin problem is suppressed and not reopened; no extra episode is created.
    assert [(e["id"], e["status"]) for e in data.load_episodes("a1")] == [("ep-0001", "handed_over")]
    pending = data.load_pending("a1")
    assert [(p["problem"], p["severity"], p["value"], p["measured_at"]) for p in pending] == [
        (OTHER, "moderate", 25.0, "2027-04-10T08:00:00")]
    assert [(r["value"], r["phase"]) for r in protocol_rows()] == [(25.0, "mission")]


def test_reading_below_thresholds_detects_nothing(storage):
    updated = engine.submit(storage, {"value": 5})
    assert (updated["status"], updated["current_node"]) == ("active", "explain")
    assert data.load_pending() == []
    assert len(protocol_rows()) == 1


def test_existing_pending_items_are_preserved(storage):
    other_astronaut = {"astronaut": "a2", "problem": OTHER, "severity": "moderate", "indicator": SIGNAL,
                       "value": 40.0, "z": None, "measured_at": "2027-04-10T06:00:00"}
    data.save_pending([other_astronaut])
    engine.submit(storage, {"value": 25})
    pending = data.load_pending()
    assert pending[0] == other_astronaut
    assert [(p["astronaut"], p["problem"]) for p in pending] == [("a2", OTHER), ("a1", OTHER)]


@pytest.mark.parametrize("value", [5, 25])
def test_reruns_and_restored_episodes_do_not_replay_detection(storage, value):
    engine.submit(storage, {"value": value})
    before = (data.load_episodes(), data.load_pending(), protocol_rows())
    restored = data.load_episodes("a1")[0]
    for _ in range(2):
        # What the Protocol page does on every rerun.
        restored = engine.submit(restored, None)
        engine.current_step(restored)
    assert (data.load_episodes(), data.load_pending(), protocol_rows()) == before


def test_check_in_can_offer_the_pending_alert_after_the_protocol_closes(storage):
    engine.submit(storage, {"value": 25})
    assert data.get_open_episode("a1") is None
    offered = episodes.accept_pending("a1", "mars")
    assert (offered["problem"], offered["status"]) == (OTHER, "pending_confirmation")
    assert data.load_pending("a1") == []


def test_reading_requires_the_episode_to_be_open_in_storage(storage):
    stale = {**storage, "id": "ep-9999"}
    with pytest.raises(ValueError, match="open episode"):
        engine.submit(stale, {"value": 25})
    assert protocol_rows() == []
    assert data.load_pending() == []
    assert [e["status"] for e in data.load_episodes("a1")] == ["active"]
