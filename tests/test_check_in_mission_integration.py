# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Check-in with real clock, symptom detection and CSV/JSON persistence.

All configuration and readings are synthetic fixtures under tmp_path. No clock,
data, detection, episode or chart functions are replaced by test doubles.
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import activity, config, data, episodes, mascot, mission, models, protocol_engine


PAGE = Path(__file__).resolve().parents[1] / "pages" / "1_Check_in.py"
START = datetime(2027, 4, 10, 8)


@pytest.fixture
def mission_workspace(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    (config_dir / "protocols").mkdir(parents=True)
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json")
    monkeypatch.setattr(models, "ACTIVITY_FILE", tmp_path / "activity.json")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", tmp_path / "astronauts.csv")
    models.ASTRONAUTS_FILE.write_text("id,name,role\na1,Synthetic A,Test\na2,Synthetic B,Test\n", encoding="utf-8")
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "switch_page", lambda destination: st.rerun())
    indicators = {key: {"name": f"Synthetic indicator {key}", "unit": "test units",
                        "how_to_measure": "Synthetic test input.", "why_it_matters": "Test fixture.",
                        "source": "none"} for key in ("x", "y")}
    problems = {}
    for key, indicator in (("synthetic_a", "x"), ("synthetic_b", "y")):
        problems[key] = {
            "name": key, "confirm_wait_min": 5, "protocol": f"protocols/{key}.json",
            "symptoms": {"reading": {"name": "Synthetic reading", "levels": [
                {"level": "concern", "when": {"indicator": indicator, "above": 15}},
                {"level": "watch", "when": {"indicator": indicator, "above": 5}},
            ]}},
            "states": [{"state": "watch", "when": {"symptom": "reading", "level_at_least": "watch"}}],
            "source": "none",
        }
        (config_dir / "protocols" / f"{key}.json").write_text(json.dumps({
            "problem": key, "start": "first", "nodes": {
                "first": {"type": "info", "text": "Synthetic step.", "next": "end"},
                "end": {"type": "end", "text": "Synthetic end.", "outcome": "resolved"},
            },
        }), encoding="utf-8")
    for filename, content in {
        "mission.json": {"start": START.isoformat(), "environment": "mars"},
        "indicators.json": indicators, "problems.json": problems,
        "checkins.json": {key: {"name": f"Check {key}", "indicators": [key], "bar_full_hours": 24} for key in ("x", "y")},
        "subjective_issues.json": {"settings": {"persistence_days": 3, "speed_multiplier": 2}, "issues": {}},
        "environments.json": {"mars": {"name": "Mars"}},
    }.items():
        (config_dir / filename).write_text(json.dumps(content), encoding="utf-8")
    for indicator, values in (("x", (8, 10, 12)), ("y", (0, 1, 2))):
        for index, value in enumerate(values):
            data.add_measurement(reading(indicator, value, START - timedelta(days=3-index), phase="preflight"))
    # Stored history must not open episodes. Future rows must stay hidden.
    data.add_measurement(reading("x", 50, START - timedelta(hours=1)))
    data.add_measurement(reading("y", 20, START + timedelta(minutes=30)))
    data.add_measurement(reading("x", 40, START + timedelta(hours=2)))
    return tmp_path


def reading(indicator, value, timestamp, phase="mission"):
    return {"timestamp": timestamp.isoformat(), "astronaut": "a1", "indicator": indicator,
            "value": value, "unit": "test units", "phase": phase, "source": "simulated"}


def screen():
    app = AppTest.from_file(str(PAGE))
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "mars"
    app.session_state["check_in_selected:a1:mars"] = "x"
    app.run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def disk_snapshot():
    paths = (models.MEASUREMENTS_FILE, models.EPISODES_FILE, models.MISSION_STATE_FILE, models.ACTIVITY_FILE)
    return tuple(path.read_bytes() if path.exists() else None for path in paths)


def stored_rows():
    with models.MEASUREMENTS_FILE.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def record_and_wait():
    app = screen()
    app.number_input[0].set_value(16)
    button(app, "Record measurement").click().run()
    assert not app.exception
    initial = data.get_open_episode("a1")
    assert initial["problem"] == "synthetic_a" and initial["status"] == "pending_confirmation"
    assert activity.bar_level("a1", "check_in", "x") == 0
    assert button(app, "Confirm repeat measurement").disabled
    assert mission.now() == START
    before_count = len(stored_rows())
    button(app, "Simulate wait").click().run()
    assert not app.exception
    assert mission.now() == START + timedelta(hours=1)
    assert len(stored_rows()) == before_count
    assert data.get_open_episode("a1") == initial
    assert [item["problem"] for item in data.load_pending("a1")] == ["synthetic_b"]
    assert not button(app, "Confirm repeat measurement").disabled
    return app, initial


def test_render_and_rerun_do_not_process_history_or_reveal_future(mission_workspace):
    before = disk_snapshot()
    app = screen()
    app.run()
    assert not app.exception
    assert disk_snapshot() == before
    assert data.load_episodes() == [] and data.load_pending() == []
    assert 20 not in data.load_measurements(indicator="y")["value"].tolist()
    assert 40 not in data.load_measurements(indicator="x")["value"].tolist()


def test_shared_wait_detects_other_astronaut_without_duplicate_rows(mission_workspace):
    data.add_measurement({**reading("y", 20, START + timedelta(minutes=30)), "astronaut": "a2"})
    count = len(stored_rows())
    app, initial = record_and_wait()
    other = data.get_open_episode("a2")
    assert other["problem"] == "synthetic_b"
    assert other["status"] == "pending_confirmation"
    assert other["environment"] == "mars"
    assert data.get_open_episode("a1") == initial
    assert len(stored_rows()) == count + 1  # Only the explicitly submitted manual reading is added.
    before = disk_snapshot()
    app.run()
    assert not app.exception
    assert disk_snapshot() == before


@pytest.mark.parametrize("repeat_value,status", [(16, "active"), (0, "dismissed")])
def test_real_wait_repeat_and_fresh_session_preserve_state(mission_workspace, repeat_value, status):
    app, initial = record_and_wait()
    app.number_input[0].set_value(repeat_value)
    button(app, "Confirm repeat measurement").click().run()
    assert not app.exception
    result = data.load_episodes()[0]
    assert result["id"] == initial["id"] and result["status"] == status
    assert result["severity"] == "watch"
    assert activity.bar_level("a1", "check_in", "x") == 100
    assert len(stored_rows()) == 11
    assert len(data.load_measurements()) == 10  # One future simulated row is still hidden.
    assert len([row for row in stored_rows() if row["source"] == "manual"]) == 2
    assert 40 not in data.load_measurements(indicator="x")["value"].tolist()
    before = disk_snapshot()
    app.run()
    restored = screen()
    assert disk_snapshot() == before
    assert mission.now() == START + timedelta(hours=1)
    assert [item["problem"] for item in data.load_pending("a1")] == ["synthetic_b"]
    if status == "active":
        assert button(restored, "Open Protocol")
    else:
        assert button(restored, "Review next alert")


def test_next_pending_starts_fresh_wait_and_reveals_only_new_rows(mission_workspace):
    app, _ = record_and_wait()
    app.number_input[0].set_value(0)
    button(app, "Confirm repeat measurement").click().run()
    count = len(stored_rows())
    button(app, "Review next alert").click().run()
    assert not app.exception
    next_episode = data.get_open_episode("a1")
    assert next_episode["problem"] == "synthetic_b"
    assert next_episode["opened_at"] == mission.now().isoformat()
    assert button(app, "Confirm repeat measurement").disabled
    assert len(stored_rows()) == count and data.load_pending() == []
    button(app, "Simulate wait").click().run()
    assert not app.exception
    assert mission.now() == START + timedelta(hours=2)
    assert len(stored_rows()) == count
    assert [item["problem"] for item in data.load_pending("a1")] == ["synthetic_a"]
    app.number_input[0].set_value(20)
    button(app, "Confirm repeat measurement").click().run()
    assert not app.exception
    assert data.get_open_episode("a1")["status"] == "active"
    assert len(stored_rows()) == count + 1
    before = disk_snapshot()
    screen()
    assert disk_snapshot() == before


@pytest.mark.parametrize("confirmation", [False, True])
def test_missing_baseline_keeps_reading_and_shows_incomplete_assessment(mission_workspace, confirmation):
    app = screen()
    initial = None
    if confirmation:
        app, initial = record_and_wait()
    # Remove this indicator's reference only, retaining the other indicator's rows.
    rows = [row for row in stored_rows() if not (row["indicator"] == "x" and row["phase"] == "preflight")]
    with models.MEASUREMENTS_FILE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=models.MEASUREMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    path = config.CONFIG_DIR / "problems.json"
    problems = json.loads(path.read_text(encoding="utf-8"))
    problems["synthetic_a"]["symptoms"]["reading"]["levels"] = [
        {"level": "concern", "when": {"indicator": "x", "metric": "baseline_delta", "above": 5}}]
    path.write_text(json.dumps(problems), encoding="utf-8")
    app.run()
    assert any("Cannot evaluate x: no valid pre-flight baseline" in item.value for item in app.warning)
    count = len(stored_rows())
    app.number_input[0].set_value(0)
    button(app, "Confirm repeat measurement" if confirmation else "Record measurement").click().run()
    assert not app.exception
    assert len(stored_rows()) == count + 1
    assert not app.success
    if confirmation:
        assert "Repeat measurement recorded" in app.error[0].value
        assert data.get_open_episode("a1") == initial
    else:
        assert any("Assessment is incomplete" in item.value for item in app.warning)
        assert data.get_open_episode("a1") is None
    before = disk_snapshot()
    app.run()
    assert not app.exception
    assert disk_snapshot() == before
    assert any("Cannot evaluate x" in item.value for item in app.warning)


def test_new_mission_alert_replaces_previous_no_alert_feedback(mission_workspace, monkeypatch):
    speech = []
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: speech.append(text))
    app = screen()
    app.number_input[0].set_value(0)
    button(app, "Record measurement").click().run()
    assert "No alert was opened" in app.success[0].value

    for measurement in mission.advance(hours=1):
        episodes.on_new_measurement(measurement, "mars")
    before = disk_snapshot()
    app.run()

    assert not app.exception
    assert not app.success
    assert "needs a repeat measurement" in speech[-1]
    button(app, "Continue repeat measurement").click().run()
    assert button(app, "Confirm repeat measurement").disabled
    assert data.get_open_episode("a1")["problem"] == "synthetic_b"
    assert disk_snapshot() == before


@pytest.mark.parametrize("finish", ["protocol", "reset"])
def test_closed_or_reset_episode_does_not_keep_confirmation_feedback(mission_workspace, monkeypatch, finish):
    speech = []
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: speech.append(text))
    app, _ = record_and_wait()
    assert "needs a repeat measurement" in speech[-1]
    app.number_input[0].set_value(16)
    button(app, "Confirm repeat measurement").click().run()
    assert "alert is confirmed" in app.success[0].value
    assert speech[-1] == "Your alert is confirmed. Open Protocol to continue with the guided steps."

    if finish == "protocol":
        result = protocol_engine.submit(data.get_open_episode("a1"), {"action": "continue"})
        assert result["status"] == "resolved"
    else:
        seed = mission_workspace / "seed"
        seed.mkdir()
        (seed / "episodes.json").write_text(json.dumps({"episodes": [], "pending": []}), encoding="utf-8")
        monkeypatch.setattr(models, "DATA_DIR", mission_workspace)
        monkeypatch.setattr(models, "SEED_DIR", seed)
        data.reset_demo()
    before = disk_snapshot()
    app.run()

    assert not app.exception
    assert data.get_open_episode("a1") is None
    assert not app.success
    assert all(item.label != "Open Protocol" for item in app.button)
    assert speech[-1] == "Choose an indicator and record a new measurement."
    assert disk_snapshot() == before


def test_grouped_submission_uses_real_detection_and_keeps_other_alert_pending(mission_workspace):
    path = config.CONFIG_DIR / 'checkins.json'
    path.write_text(json.dumps({'x': {'name': 'Synthetic paired test', 'indicators': ['x', 'y'],
                                     'bar_full_hours': 24}}), encoding='utf-8')
    app = screen()
    assert len(app.number_input) == 2
    app.number_input[0].set_value(16)
    app.number_input[1].set_value(20)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert data.get_open_episode('a1')['problem'] == 'synthetic_a'
    assert [item['problem'] for item in data.load_pending('a1')] == ['synthetic_b']
    assert [(row['indicator'], row['value']) for row in stored_rows() if row['source'] == 'manual'] == [
        ('x', '16.0'), ('y', '20.0')]
    assert len(app.number_input) == 1
    assert activity.bar_level('a1', 'check_in', 'x') == 0
    before = disk_snapshot()
    app.run()
    assert disk_snapshot() == before
