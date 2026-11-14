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
from streamlit.testing.v1 import AppTest

from core import config, data, mascot, mission, models


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
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
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
    app.run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def disk_snapshot():
    paths = (models.MEASUREMENTS_FILE, models.EPISODES_FILE, models.MISSION_STATE_FILE)
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


@pytest.mark.parametrize("repeat_value,status", [(16, "active"), (0, "dismissed")])
def test_real_wait_repeat_and_fresh_session_preserve_state(mission_workspace, repeat_value, status):
    app, initial = record_and_wait()
    app.number_input[0].set_value(repeat_value)
    button(app, "Confirm repeat measurement").click().run()
    assert not app.exception
    result = data.load_episodes()[0]
    assert result["id"] == initial["id"] and result["status"] == status
    assert result["severity"] == "watch"
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
