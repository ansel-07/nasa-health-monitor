# AI-assisted: generated with Claude Code and reviewed by Javi (review pending).
"""Tutorials page (#97): gate at 80 / 70, a practice run saves nothing but the tutorial bar."""
from datetime import datetime

import pytest
from streamlit.testing.v1 import AppTest

from core import activity, config, mission, models


@pytest.fixture
def storage(tmp_path, monkeypatch):
    for name in ("MEASUREMENTS_FILE", "EPISODES_FILE", "MISSION_STATE_FILE", "ACTIVITY_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    monkeypatch.setattr(models, "DATA_DIR", tmp_path)
    monkeypatch.setattr(mission, "now", lambda: datetime(2027, 4, 10, 8))
    example = config.load_problems(include_examples=True)["_example"]
    monkeypatch.setattr(config, "load_problems", lambda include_examples=False: {"_example": example})
    return tmp_path


def page():
    app = AppTest.from_file("../app.py").run()
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "mars"
    app.switch_page("pages/4_Tutorials.py").run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


@pytest.mark.parametrize("level,enabled", [(100, False), (80, False), (70, True), (0, True)])
def test_start_is_gated_by_the_bar(storage, monkeypatch, level, enabled):
    monkeypatch.setattr(activity, "bar_level", lambda astronaut, kind, activity_id: level)
    assert button(page(), "Start tutorial").disabled is not enabled


def test_practice_run_saves_nothing_and_refills_the_bar(storage):
    app = page()
    button(app, "Start tutorial").click().run()
    button(app, "Continue").click().run()                   # intro_mars
    button(app, "No").click().run()                         # one click per answer
    button(app, "Done").click().run()                       # do_action, no wait in practice
    app.number_input[0].set_value(25)
    next(f for f in app.get("form_submit_button") if f.label == "Continue").click().run()
    button(app, "Continue").click().run()                   # contact the flight surgeon
    assert not app.exception
    assert any("Tutorial completed" in item.value for item in app.success)
    assert [path.name for path in storage.iterdir()] == ["activity.json"]
    assert activity.bar_level("a1", "tutorial", "_example") == 100
    assert button(app, "Back to Tutorials")


def test_no_mascot_and_no_voice_on_tutorials(storage):
    """docs/FRONTEND_MASCOT_LAYOUT.md 6: the list and the practice run have no mascot."""
    app = page()
    assert not app.get("iframe") and all(item.label != "Voice" for item in app.toggle)
    button(app, "Start tutorial").click().run()
    assert not app.exception
    assert not app.get("iframe") and all(item.label != "Voice" for item in app.toggle)
    assert app.markdown and app.get("graphviz_chart")


def test_cannot_on_a_step_that_loops_back_says_it_stays_open(storage, monkeypatch):
    from copy import deepcopy
    from core import protocol_engine
    protocol = config.load_protocol("_example")
    protocol["nodes"]["do_action"]["next_if_cannot"] = "do_action"   # like the handover hold
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    note = "Noted. This step stays open until you can select Done."
    app = page()
    button(app, "Start tutorial").click().run()
    button(app, "Continue").click().run()                   # intro_mars
    button(app, "No").click().run()                         # -> do_action
    assert not any(item.value == note for item in app.info)
    button(app, "I can't").click().run()
    assert any(item.value == note for item in app.info)
    button(app, "Done").click().run()
    assert not any(item.value == note for item in app.info)
    assert not app.exception
