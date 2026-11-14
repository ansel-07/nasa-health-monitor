# AI-assisted: generated with Codex; human review pending.
"""Exercise Protocol controls with Streamlit's AppTest and isolated core APIs."""
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import config, data, episodes, mascot, mission, protocol_engine


@pytest.fixture
def context(monkeypatch):
    episode = {"id": "ep-page", "astronaut": "a1", "problem": "test_issue",
               "environment": "mars", "status": "active", "severity": "moderate",
               "severity_initial": "moderate", "current_node": "intro",
               "vars": {}, "answers": {}, "log": []}
    state = {"episode": episode, "pending": [], "clock": datetime(2027, 4, 10, 8)}
    protocol = config.load_protocol("_example")
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    monkeypatch.setattr(config, "load_problems", lambda: {"test_issue": {"name": "Test issue"}})
    monkeypatch.setattr(data, "get_open_episode", lambda astronaut: (
        deepcopy(state["episode"]) if state["episode"] and state["episode"]["astronaut"] == astronaut
        and state["episode"]["status"] in ("active", "pending_confirmation") else None))
    monkeypatch.setattr(data, "load_episodes", lambda astronaut: (
        [deepcopy(state["episode"])] if state["episode"] and state["episode"]["astronaut"] == astronaut else []))
    monkeypatch.setattr(data, "save_episode", lambda episode: state.update(episode=deepcopy(episode)))
    monkeypatch.setattr(data, "latest_values", lambda _: {})
    state["measurements"] = Mock()
    monkeypatch.setattr(data, "add_measurement", state["measurements"])
    monkeypatch.setattr(episodes, "get_pending", lambda astronaut: deepcopy(state["pending"]))
    monkeypatch.setattr(mission, "now", lambda: state["clock"])
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: st.info(text))
    return state


def page(astronaut="a1"):
    app = AppTest.from_file("../app.py").run()
    if astronaut:
        app.session_state["astronaut"] = astronaut
    else:
        del app.session_state["astronaut"]
    app.switch_page("pages/2_Protocol.py").run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_requires_astronaut(context):
    app = page(None)
    assert any("Choose an astronaut" in item.value for item in app.info)
    assert not app.button


def test_no_episode_and_pending(context):
    context["episode"] = None
    context["pending"] = [{"problem": "test_issue", "severity": "severe"}]
    app = page()
    assert any("no active protocol" in item.value for item in app.info)
    assert any("Next: Test issue (severe)" in item.value for item in app.info)


def test_pending_confirmation_has_no_protocol_controls(context):
    context["episode"]["status"] = "pending_confirmation"
    app = page()
    assert any("repeat measurement" in item.value for item in app.info)
    assert not app.button
    assert context["episode"]["log"] == []


def test_info_advances_and_question_requires_selection(context):
    app = page()
    button(app, "Continue").click().run()
    assert not app.exception
    assert context["episode"]["current_node"] == "symptoms"
    button(app, "Submit answer").click().run()
    assert app.error[0].value == "Choose an answer before continuing."
    app.radio[0].set_value("no")
    button(app, "Submit answer").click().run()
    assert not app.exception
    assert context["episode"]["answers"] == {"has_symptom": "no"}
    assert button(app, "Done").disabled
    assert not button(app, "I can't").disabled


def test_timed_action_refresh_and_measurement(context):
    context["episode"]["current_node"] = "do_action"
    app = page()
    assert button(app, "Done").disabled
    context["clock"] = datetime(2027, 4, 10, 8, 1)
    button(app, "Refresh wait").click().run()
    assert not button(app, "Done").disabled
    button(app, "Done").click().run()
    assert not app.exception
    assert context["episode"]["current_node"] == "remeasure"
    button(app, "Save measurement").click().run()
    assert app.error[0].value == "Enter a measurement before continuing."
    context["measurements"].assert_not_called()
    app.number_input[0].set_value(8)
    button(app, "Save measurement").click().run()
    assert not app.exception
    context["measurements"].assert_called_once()
    assert context["episode"]["status"] == "resolved"
    assert app.success[0].value == "Protocol completed: Resolved"
    app.run()
    assert app.success[0].value == "Protocol completed: Resolved"
    context["measurements"].assert_called_once()
    # Reset or astronaut switching must not display an obsolete result.
    context["episode"] = None
    app.run()
    assert not app.success


def test_contact_displays_configured_delay_and_finishes(context, monkeypatch):
    context["episode"]["current_node"] = "contact_now"
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"mars": {"comm_delay_min": 7}})
    app = page()
    assert any("14 minutes" in item.value for item in app.caption)
    button(app, "Continue").click().run()
    assert not app.exception
    assert context["episode"]["status"] == "handed_over"
    assert app.success[0].value == "Protocol completed: Handed over"


def test_cannot_during_wait_routes_to_crew(context, monkeypatch):
    context["episode"]["current_node"] = "do_action"
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"mars": {"comm_delay_min": 7}})
    app = page()
    button(app, "I can't").click().run()
    assert not app.exception
    assert context["episode"]["current_node"] == "contact_crew"
    button(app, "Continue").click().run()
    assert context["episode"]["status"] == "monitoring"


def test_missing_contact_delay_blocks_controls(context):
    context["episode"]["current_node"] = "contact_now"
    app = page()
    assert app.error
    assert not app.button


def test_examples_are_never_executed(context):
    context["episode"]["problem"] = "_example"
    app = page()
    assert not app.button
    assert context["episode"]["log"] == []


def test_other_astronaut_cannot_see_episode(context):
    app = page("a2")
    assert any("no active protocol" in item.value for item in app.info)
    assert not app.success


def test_save_error_keeps_current_step(context, monkeypatch):
    app = page()
    monkeypatch.setattr(data, "save_episode", Mock(side_effect=OSError("Storage unavailable")))
    button(app, "Continue").click().run()
    assert not app.exception
    assert app.error
    assert context["episode"]["current_node"] == "intro"
