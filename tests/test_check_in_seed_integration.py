# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Protect the published Check-in demo against seed/config/UI integration regressions.

Use the real seed and configuration, copying runtime data into a temporary browser
session. Repeat the seed's synthetic reading; never invent a medical test value.
"""
from pathlib import Path

import pytest
from streamlit.runtime.pages_manager import PagesManager
from streamlit.testing.v1 import AppTest

from core import activity, config, data, mascot, models


APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_real_seed_check_in_confirms_without_incomplete_baselines(tmp_path, monkeypatch, environment):
    initialize_pages = PagesManager.__init__

    def explicit_navigation(self, *args, **kwargs):
        # AppTest resets navigation discovery; live sessions retain explicit mode.
        PagesManager.uses_pages_directory = False
        initialize_pages(self, *args, **kwargs)

    monkeypatch.setattr(PagesManager, "__init__", explicit_navigation)
    monkeypatch.setattr(models, "SESSION_DATA", True)
    monkeypatch.setattr(models, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(models, "_session_id", lambda: "check-in-seed-regression")
    monkeypatch.setattr(mascot, "say", lambda *args, **kwargs: None)
    seed_before = {path.name: path.read_bytes() for path in models.SEED_DIR.iterdir() if path.is_file()}
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = environment

    def click(label):
        next(button for button in app.button if button.label == label).click().run()
        assert not app.exception

    def assert_assessments_available():
        assert not any("incomplete" in item.value.lower() or "cannot evaluate" in item.value.lower()
                       for item in app.warning)

    app.run()
    assert not app.exception
    for key in ("welcome_astronaut_a1", f"welcome_environment_{environment}"):  # Welcome buttons
        app.button(key=key).click().run()
        assert not app.exception
    assert data.load_episodes("a1") == []  # Stored simulated history never opens an episode.
    required_indicators = {key for item in config.load_checkins().values() for key in item["indicators"]}
    preflight = data.load_measurements(astronaut="a1", phase="preflight")
    assert required_indicators <= set(preflight["indicator"])
    click("Advance mission 24 h")
    initial = data.get_open_episode("a1")
    assert initial["problem"] == "sans"
    assert initial["status"] == "pending_confirmation"
    assert initial["environment"] == environment
    assert initial["trigger"]["indicator"] == "peripapillary_trt_left"
    click("Check-in")
    assert_assessments_available()
    assert len(app.number_input) == 1  # Repeat only the indicator that opened the alert.
    assert next(button for button in app.button if button.label == "Confirm repeat measurement").disabled
    click("Simulate wait")
    assert_assessments_available()
    assert not app.number_input[0].disabled
    app.number_input[0].set_value(initial["trigger"]["value"])
    click("Confirm repeat measurement")

    confirmed = data.get_open_episode("a1")
    assert confirmed["id"] == initial["id"] and confirmed["status"] == "active"
    assert [title.value for title in app.title] == ["Protocol"]
    checkin_id = next(key for key, item in config.load_checkins().items()
                      if initial["trigger"]["indicator"] in item["indicators"])
    assert activity.bar_level("a1", "check_in", checkin_id) == 100
    app.run()
    assert not app.exception
    assert data.get_open_episode("a1")["id"] == initial["id"]
    assert len(data.load_episodes("a1")) == 1
    manual = data.load_measurements(astronaut="a1", phase="mission").query("source == 'manual'")
    assert len(manual) == 1 and manual.iloc[0]["indicator"] == initial["trigger"]["indicator"]
    assert {path.name: path.read_bytes() for path in models.SEED_DIR.iterdir() if path.is_file()} == seed_before
