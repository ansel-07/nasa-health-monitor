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
    # Protocol readings are stored through detection (episodes.on_new_measurement).
    monkeypatch.setattr(episodes, "on_new_measurement", state["measurements"])
    monkeypatch.setattr(episodes, "get_pending", lambda astronaut: deepcopy(state["pending"]))
    monkeypatch.setattr(mission, "now", lambda: state["clock"])
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: st.info(text))
    return state


def page(astronaut="a1"):
    app = AppTest.from_file("../app.py").run()
    if astronaut:
        app.session_state["astronaut"] = astronaut
    elif "astronaut" in app.session_state:  # the Welcome no longer pre-selects one
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
    assert any("Next: Test issue (Severe)" in item.value for item in app.info)


def test_pending_confirmation_has_no_protocol_controls(context):
    context["episode"]["status"] = "pending_confirmation"
    app = page()
    assert any("repeat measurement" in item.value for item in app.info)
    assert not app.button
    assert context["episode"]["log"] == []


def test_info_advances_and_question_answers_in_one_click(context):
    app = page()
    button(app, "Continue").click().run()
    assert not app.exception
    assert context["episode"]["current_node"] == "symptoms"
    assert not app.radio and not app.get("form_submit_button")
    button(app, "No").click().run()
    assert not app.exception
    assert context["episode"]["answers"] == {"has_symptom": "no"}
    assert button(app, "Done").disabled
    assert not button(app, "I can't").disabled


def test_astronaut_sees_readable_names_not_internal_ids(context, monkeypatch):
    protocol = protocol_engine.load_protocol("_example")  # the fixture copy from context
    protocol["nodes"]["symptoms"]["options"] = {"yes": "escalate", "not_yet": "do_action"}
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    monkeypatch.setattr(config, "load_environments", lambda: {"mars": {"name": "Synthetic Mars base"}})
    context["episode"].update(current_node="symptoms", severity="medical_urgency")
    app = page()
    assert any(item.value == "Severity: Medical urgency · Environment: Synthetic Mars base" for item in app.caption)
    assert {"Yes", "Not yet"} <= {item.label for item in app.button}
    button(app, "Not yet").click().run()
    assert context["episode"]["answers"] == {"has_symptom": "not_yet"}


def test_completion_time_is_readable(context, monkeypatch):
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"mars": {"comm_delay_min": 7}})
    context["episode"]["current_node"] = "contact_now"
    button(page(), "Continue").click().run()
    app = page()
    assert any(item.value == "Completed at mission time 10 Apr 2027, 08:00" for item in app.caption)


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


@pytest.mark.parametrize("one_way,shown", [
    (0, "less than 1 second"), (1.27 / 60, "about 3 seconds"), (0.25, "about 30 seconds"),
    (0.5, "1 minute"), (7, "14 minutes"), (10.26, "20.5 minutes")])
def test_contact_delay_is_readable_and_zero_is_valid(context, monkeypatch, one_way, shown):
    # Synthetic one-way delays; the step shows the round trip (2 x one-way).
    context["episode"].update(current_node="contact_now", environment="iss")
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"iss": {"comm_delay_min": one_way}})
    app = page()
    assert not app.error
    assert any(item.value == f"Signal round trip to Earth: {shown}. A clinical answer can take longer."
               for item in app.caption)
    assert button(app, "Continue")


def test_cannot_during_wait_routes_to_crew(context, monkeypatch):
    context["episode"]["current_node"] = "do_action"
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"mars": {"comm_delay_min": 7}})
    app = page()
    button(app, "I can't").click().run()
    assert not app.exception
    assert context["episode"]["current_node"] == "contact_crew"
    button(app, "Continue").click().run()
    assert context["episode"]["status"] == "monitoring"


@pytest.mark.parametrize("mars", [{"comm_delay_min": "TODO_EDU"}, {}])
def test_missing_contact_delay_blocks_controls(context, monkeypatch, mars):
    # Fixture environments, so the test does not depend on the real values in config/.
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {"mars": mars})
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


def current_in_chart(app) -> str:
    charts = app.get("graphviz_chart")
    assert len(charts) == 1
    return next(line.split('"')[1] for line in charts[0].proto.spec.splitlines() if f'fillcolor="{protocol_engine._CURRENT[0]}"' in line)


def test_flowchart_beside_mascot_follows_the_current_step(context):
    app = page()
    assert current_in_chart(app) == "intro"
    assert button(app, "Continue")
    button(app, "Continue").click().run()
    assert current_in_chart(app) == "symptoms"
    assert button(app, "Yes") and button(app, "No")


def test_screens_without_an_active_protocol_show_no_flowchart(context):
    episode = context["episode"]
    context["episode"] = {**episode, "status": "pending_confirmation"}
    assert not page().get("graphviz_chart")
    context["episode"] = None
    assert not page().get("graphviz_chart")


def test_flowchart_is_focused_by_default_and_whole_on_request(context):
    app = page()
    focused = app.get("graphviz_chart")[0].proto.spec
    assert '"handed_over" [' not in focused  # far from the current step
    app.toggle(key="protocol_whole_a1").set_value(True).run()
    whole = app.get("graphviz_chart")[0].proto.spec
    for node_id in protocol_engine.load_protocol("_example")["nodes"]:
        assert f'"{node_id}" [' in whole
    assert current_in_chart(app) == "intro"


def test_lists_active_protocol_and_all_pending_by_severity(context):
    # get_pending already returns the queue most severe first (episodes.get_pending).
    context["pending"] = [{"problem": "test_issue", "severity": "severe"},
                          {"problem": "test_issue", "severity": "mild"}]
    app = page()
    assert any(item.value == "Your protocols" for item in app.subheader)
    text = "\n".join(item.value for item in app.markdown)
    assert "In progress" in text
    assert text.index("Severity: Severe · Waiting") < text.index("Severity: Mild · Waiting")


def test_cannot_is_hidden_when_the_step_has_no_route(context, monkeypatch):
    protocol = protocol_engine.load_protocol("_example")  # the fixture copy from context
    protocol["nodes"]["do_action"].pop("next_if_cannot")
    protocol["nodes"]["do_action"].pop("wait_min", None)
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    context["episode"]["current_node"] = "do_action"
    app = page()
    labels = [item.label for item in app.button]
    assert "Done" in labels and "I can't" not in labels


@pytest.mark.parametrize("environment", ["mars", "iss", "moon"])
def test_local_medical_officer_shows_no_earth_delay(context, monkeypatch, environment):
    # #141: the crew medical officer is on board; only Earth contacts show signal time.
    context["episode"].update(current_node="contact_crew", environment=environment)
    monkeypatch.setattr(protocol_engine, "load_environments", lambda: {environment: {"comm_delay_min": 22}})
    app = page()
    assert not app.error
    captions = [item.value for item in app.caption]
    assert "On board: no Earth signal delay." in captions
    assert not any("Signal round trip" in text or "minutes" in text for text in captions)


def test_cannot_on_a_step_that_loops_back_says_it_stays_open(context, monkeypatch):
    # A self-looping "I can't" (like the handover hold) keeps the same step and text;
    # the page must say so, or the button looks like it did nothing.
    protocol = protocol_engine.load_protocol("_example")  # the fixture copy from context
    protocol["nodes"]["do_action"].update(next_if_cannot="do_action")
    protocol["nodes"]["do_action"].pop("wait_min", None)
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    context["episode"]["current_node"] = "do_action"
    note = "Noted. This step stays open until you can select Done."
    app = page()
    assert not any(item.value == note for item in app.info)
    button(app, "I can't").click().run()
    assert context["episode"]["current_node"] == "do_action"
    assert any(item.value == note for item in app.info)
    button(app, "Done").click().run()
    assert context["episode"]["current_node"] != "do_action"
    assert not any(item.value == note for item in app.info)


def test_cannot_that_leads_elsewhere_shows_no_hold_note(context, monkeypatch):
    protocol = protocol_engine.load_protocol("_example")
    protocol["nodes"]["do_action"].pop("wait_min", None)
    monkeypatch.setattr(protocol_engine, "load_protocol", lambda _: deepcopy(protocol))
    context["episode"]["current_node"] = "do_action"
    app = page()
    button(app, "I can't").click().run()
    assert context["episode"]["current_node"] == "contact_crew"
    assert not any("stays open" in item.value for item in app.info)
