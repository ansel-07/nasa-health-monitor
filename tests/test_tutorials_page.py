# AI-assisted: generated with Claude Code and reviewed by Javi.
"""Tutorials page (#97): gate at 80 / 70, a practice run saves nothing but the tutorial bar."""
from datetime import datetime

import pytest
from streamlit.testing.v1 import AppTest

from core import activity, config, mission, models, protocol_engine


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


def start(app):
    """Open the _example tutorial: the whole ui.card is its button (#233)."""
    next(item for item in app.button if item.key == "tutorial_card:_example").click().run()


@pytest.mark.parametrize("level,enabled", [(100, False), (80, False), (70, True), (0, True)])
def test_start_is_gated_by_the_bar(storage, monkeypatch, level, enabled):
    monkeypatch.setattr(activity, "bar_level", lambda astronaut, kind, activity_id: level)
    app = page()
    if not enabled:   # the card's status line says when it can be repeated
        assert any(f"Ready below 80% · now {level}%" in str(item.proto) for item in app.get("html"))
    start(app)
    assert not app.exception
    assert ("tutorial_run" in app.session_state) is enabled
    if not enabled:   # clicking a card that is not ready explains why, without starting
        assert any(f"drops below 80% (now {level}%)" in item.value for item in app.info)


def test_practice_run_saves_nothing_and_refills_the_bar(storage):
    app = page()
    start(app)
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


def test_failed_completion_write_keeps_practice_retryable(storage, monkeypatch):
    app = page()
    start(app)
    for label in ("Continue", "No", "Done"):
        button(app, label).click().run()
    app.number_input[0].set_value(25)
    next(f for f in app.get("form_submit_button") if f.label == "Continue").click().run()
    complete = activity.complete
    attempts = []

    def fail_once(*args):
        attempts.append(args)
        if len(attempts) == 1:
            raise OSError("Synthetic completion storage failure")
        complete(*args)

    monkeypatch.setattr(activity, "complete", fail_once)
    before = app.session_state["tutorial_run"]
    assert protocol_engine.current_step(before)["type"] == "contact"
    button(app, "Continue").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state["tutorial_run"] == before
    assert not list(storage.iterdir())
    button(app, "Continue").click().run()
    assert not app.exception
    assert any("Tutorial completed" in item.value for item in app.success)
    assert activity.bar_level("a1", "tutorial", "_example") == 100


def test_no_mascot_and_no_voice_on_tutorials(storage):
    """docs/FRONTEND_MASCOT_LAYOUT.md 6: the list and the practice run have no mascot."""
    app = page()
    assert not app.get("iframe") and all(item.label != "Voice" for item in app.toggle)
    start(app)
    assert not app.exception
    assert not app.get("iframe") and all(item.label != "Voice" for item in app.toggle)
    assert app.markdown and app.get("graphviz_chart")


def test_changing_the_environment_ends_the_practice_run(storage):
    """A run started on Mars must not keep following Mars branches after the Welcome picks another environment."""
    app = page()
    start(app)
    assert app.session_state["tutorial_run"]["environment"] == "mars"
    app.session_state["environment"] = "moon"
    app.run()
    assert "tutorial_run" not in app.session_state
    assert any(item.key == "tutorial_card:_example" for item in app.button)   # back on the list
    start(app)
    assert app.session_state["tutorial_run"]["environment"] == "moon"
    assert not app.exception


def test_whole_protocol_opens_in_a_dialog(storage):
    """#233: "Show whole protocol" opens the whole diagram in a dialog; the focused chart stays."""
    app = page()
    start(app)
    focused = app.get("graphviz_chart")[0].proto.spec
    next(b for b in app.button if b.key == "tutorial_whole").click().run()
    assert not app.exception
    specs = [chart.proto.spec for chart in app.get("graphviz_chart")]
    assert len(specs) == 2 and specs[0] == focused
    for node_id in config.load_protocol("_example")["nodes"]:
        assert f'"{node_id}" [' in specs[1]


def test_main_practice_actions_are_primary_like_protocols(storage):
    """#233: Continue / Done primary; "I can't", answers and Leave tutorial stay secondary."""
    app = page()
    start(app)
    kind = lambda label: next(item for item in app.button if item.label == label).proto.type
    assert kind("Continue") == "primary" and kind("Leave tutorial") == "secondary"
    button(app, "Continue").click().run()                   # intro_mars -> question
    assert kind("Yes") == "secondary" and kind("No") == "secondary"
    button(app, "No").click().run()                         # -> do_action
    assert kind("Done") == "primary" and kind("I can't") == "secondary"


def test_out_of_domain_practice_value_shows_why_and_stays(storage, monkeypatch):
    """#247: practice measure steps use the same domain check (nothing is saved anyway)."""
    from copy import deepcopy
    from core import protocol_engine
    indicators = deepcopy(protocol_engine.load_indicators())
    indicators["_example_indicator"]["valid"] = {"min": 0}
    monkeypatch.setattr(protocol_engine, "load_indicators", lambda: indicators)
    app = page()
    start(app)
    button(app, "Continue").click().run()                   # intro_mars
    button(app, "No").click().run()
    button(app, "Done").click().run()                       # -> remeasure
    app.number_input[0].set_value(-1)
    next(f for f in app.get("form_submit_button") if f.label == "Continue").click().run()
    assert not app.exception
    assert any("cannot be below 0" in item.value for item in app.error)
    assert app.session_state["tutorial_run"]["current_node"] == "remeasure"
