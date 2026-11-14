# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Exercise the real multipage app and per-session storage with synthetic fixtures.

AppTest uses one fixed session id, so the fixture supplies distinct browser ids.
The harness preserves explicit st.navigation mode across AppTest runs. Storage
and configuration are temporary; charts, clock, detection and protocols are real.
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.testing.v1 import AppTest

from core import activity, config, data, episodes, mascot, mission, models


APP = Path(__file__).resolve().parents[1] / "app.py"
START = datetime(2027, 4, 10, 8)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    # AppTest 1.67 resets navigation detection before each run. With a pages/
    # folder it otherwise runs legacy navigation and skips app.py after a click.
    # Live sessions retain explicit-navigation mode after the first st.navigation.
    initialize_pages = PagesManager.__init__

    def explicit_navigation(self, *args, **kwargs):
        PagesManager.uses_pages_directory = False
        initialize_pages(self, *args, **kwargs)

    monkeypatch.setattr(PagesManager, "__init__", explicit_navigation)
    config_dir, seed = tmp_path / "config", tmp_path / "seed"
    (config_dir / "protocols").mkdir(parents=True)
    seed.mkdir()
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(models, "SESSION_DATA", True)
    monkeypatch.setattr(models, "SEED_DIR", seed)
    monkeypatch.setattr(models, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(models, "DATA_DIR", tmp_path / "unused-runtime")
    current = {"id": "browser-a"}
    monkeypatch.setattr(models, "_session_id", lambda: current["id"])
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
    indicators = {key: {"name": f"Synthetic {key}", "unit": "test units", "source": "fixture",
                        "how_to_measure": "Synthetic test input.", "why_it_matters": "Test fixture."}
                  for key in ("x", "y")}
    problems = {}
    for pid, indicator in (("synthetic_a", "x"), ("synthetic_b", "y")):
        problems[pid] = {"name": pid, "confirm_wait_min": 5, "protocol": f"protocols/{pid}.json",
            "symptoms": {"reading": {"name": "Synthetic reading", "levels": [{"level": "watch",
                "when": {"indicator": indicator, "metric": "baseline_delta", "above": 5}}]}},
            "states": [{"state": "watch", "when": {"symptom": "reading", "level_is": "watch"}}]}
        (config_dir / "protocols" / f"{pid}.json").write_text(json.dumps({"problem": pid,
            "start": "first", "nodes": {
                "first": {"type": "info", "text": "Synthetic step.", "next": "end"},
                "end": {"type": "end", "text": "Synthetic end.", "outcome": "resolved"}}}), encoding="utf-8")
    for filename, content in {
        "mission.json": {"start": START.isoformat(), "environment": "mars"},
        "indicators.json": indicators, "problems.json": problems,
        "checkins.json": {key: {"name": f"Check {key}", "indicators": [key], "bar_full_hours": 24} for key in ("x", "y")},
        "subjective_issues.json": {"settings": {"persistence_days": 3, "speed_multiplier": 2}, "issues": {}},
        "environments.json": {key: {"name": key.upper(), "comm_delay_min": 0, "gravity_g": 1}
                              for key in ("iss", "moon", "mars")},
    }.items():
        (config_dir / filename).write_text(json.dumps(content), encoding="utf-8")
    (seed / "astronauts.csv").write_text("id,name,role\na1,Synthetic A,Test\na2,Synthetic B,Test\n", encoding="utf-8")
    (seed / "episodes.json").write_text(json.dumps({"episodes": [], "pending": []}), encoding="utf-8")
    (seed / "mission_state.json").write_text(json.dumps({"now": START.isoformat()}), encoding="utf-8")
    with (seed / "measurements.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=models.MEASUREMENT_COLUMNS)
        writer.writeheader()
        for indicator, values in (("x", (8, 10, 12)), ("y", (0, 1, 2))):
            for index, value in enumerate(values):
                writer.writerow(reading(indicator, value, START - timedelta(days=3-index), "preflight"))
        writer.writerow(reading("x", 50, START - timedelta(hours=1)))
        for indicator in ("x", "y"):
            writer.writerow(reading(indicator, 20, START + timedelta(hours=12)))
    return current, seed


def reading(indicator, value, timestamp, phase="mission"):
    return {"timestamp": timestamp.isoformat(), "astronaut": "a1", "indicator": indicator,
            "value": value, "unit": "test units", "phase": phase, "source": "simulated"}


def snapshot(folder):
    return {path.name: path.read_bytes() for path in folder.iterdir() if path.is_file()}


def browser(environment="mars"):
    """Welcome -> NEXT -> Main Menu (docs/ASTRONAUT_HEALTH_APP_SPEC.md screens 1-2)."""
    app = AppTest.from_file(str(APP))
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = environment
    app.run()
    assert not app.exception
    click(app, "NEXT")
    return app


def click(app, label):
    next(item for item in app.button if item.label == label).click().run()
    assert not app.exception


def back_to_menu(app):
    labels = [item.label for item in app.button]
    assert "← Main Menu" in labels, (labels, [item.value for item in app.title])
    click(app, "← Main Menu")


@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_menu_confirmation_protocol_and_next_alert(workspace, environment):
    _, seed = workspace
    seed_before = snapshot(seed)
    app = browser(environment)
    assert data.load_episodes() == []  # Stored history never opens episodes.
    click(app, "Advance mission 24 h")
    initial = data.get_open_episode("a1")
    assert initial["problem"] == "synthetic_a" and initial["environment"] == environment
    assert [item["problem"] for item in data.load_pending("a1")] == ["synthetic_b"]
    click(app, "Check-in")
    assert next(item for item in app.button if item.label == "Confirm repeat measurement").disabled
    click(app, "Simulate wait")
    app.number_input[0].set_value(20)
    click(app, "Confirm repeat measurement")
    assert data.get_open_episode("a1")["status"] == "active"
    assert [item.value for item in app.title] == ["Protocol"]
    click(app, "Continue")
    assert data.get_open_episode("a1") is None
    assert data.load_episodes()[0]["status"] == "resolved"
    back_to_menu(app)
    click(app, "Check-in")
    click(app, "Review next alert")
    next_episode = data.get_open_episode("a1")
    assert next_episode["problem"] == "synthetic_b"
    assert next_episode["opened_at"] == mission.now().isoformat()
    assert next(item for item in app.button if item.label == "Confirm repeat measurement").disabled
    assert data.load_pending("a1") == []
    before = snapshot(models.data_dir())
    app.run()
    assert not app.exception
    assert snapshot(models.data_dir()) == before
    assert snapshot(seed) == seed_before


def test_second_session_and_reset_do_not_change_first_session(workspace):
    current, seed = workspace
    seed_before = snapshot(seed)
    first = browser()
    click(first, "Advance mission 24 h")
    first_folder = models.data_dir()
    first_before = snapshot(first_folder)
    assert data.get_open_episode("a1") is not None
    current["id"] = "browser-b"
    second = browser()
    assert data.load_episodes() == []
    assert mission.now() == START
    click(second, "Advance mission 24 h")
    click(second, "Reset demo")
    assert data.load_episodes() == [] and mission.now() == START
    assert snapshot(first_folder) == first_before
    assert snapshot(seed) == seed_before
    current["id"] = "browser-a"
    first.run()
    assert not first.exception
    assert data.get_open_episode("a1")["problem"] == "synthetic_a"
    assert snapshot(first_folder) == first_before


@pytest.mark.parametrize("failure", ["completion", "partial_recording"])
def test_reset_after_storage_failure_allows_a_fresh_check_in(workspace, monkeypatch, failure):
    """Exercise #132 with real storage, failure state and the actual Menu reset."""
    _, seed = workspace
    if failure == "partial_recording":
        checkins_path = config.CONFIG_DIR / "checkins.json"
        checkins_path.write_text(json.dumps({"x": {
            "name": "Check x", "indicators": ["x", "y"], "bar_full_hours": 24,
        }}), encoding="utf-8")
    seed_before = snapshot(seed)
    fail_once = [True]
    original_complete = activity.complete
    original_record = episodes.on_new_measurement

    def complete(*args, **kwargs):
        if failure == "completion" and fail_once[0]:
            fail_once[0] = False
            raise OSError("Synthetic completion storage failure")
        return original_complete(*args, **kwargs)

    def record(measurement, environment):
        if failure == "partial_recording" and measurement["indicator"] == "y" and fail_once[0]:
            fail_once[0] = False
            raise OSError("Synthetic partial recording failure")
        return original_record(measurement, environment)

    monkeypatch.setattr(activity, "complete", complete)
    monkeypatch.setattr(episodes, "on_new_measurement", record)
    app = browser()
    app.session_state["voice_on"] = False
    app.session_state["tutorial_run"] = {"kept": True}
    mission.advance_and_detect(1, "mars")
    click(app, "Check-in")
    click(app, "Check x")
    for field in app.number_input:
        field.set_value(0)
    click(app, "Record measurement")
    assert app.error and not app.success
    assert len(data.load_measurements(astronaut="a1").query("source == 'manual'")) == 1
    retry_key = ("check_in_completion:a1:mars:x" if failure == "completion"
                 else "check_in_draft:a1:mars:x")
    assert retry_key in app.session_state
    assert all(field.disabled for field in app.number_input)
    assert activity.bar_level("a1", "check_in", "x") == 0

    back_to_menu(app)
    click(app, "Reset demo")
    assert not any(str(key).startswith("check_in_") for key in app.session_state.keys())
    assert app.session_state["astronaut"] == "a1" and app.session_state["environment"] == "mars"
    assert app.session_state["voice_on"] is False
    assert app.session_state["tutorial_run"] == {"kept": True}
    assert mission.now() == START
    assert data.load_measurements(astronaut="a1").query("source == 'manual'").empty
    assert data.load_episodes() == [] and data.load_pending() == []
    assert activity.bar_level("a1", "check_in", "x") == 0

    click(app, "Check-in")
    assert not app.error
    assert all(button.label != "Finish check-in" for button in app.button)
    click(app, "Check x")
    assert all(field.value is None and not field.disabled for field in app.number_input)
    assert not next(button.disabled for button in app.button if button.label == "Record measurement")
    count = len(app.number_input)
    for field in app.number_input:
        field.set_value(0)
    click(app, "Record measurement")
    assert app.success and not app.error
    assert activity.bar_level("a1", "check_in", "x") == 100
    app.run()
    assert not app.exception
    assert len(data.load_measurements(astronaut="a1").query("source == 'manual'")) == count
    assert data.load_episodes() == [] and data.load_pending() == []
    assert snapshot(seed) == seed_before
