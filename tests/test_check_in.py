# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Check-in interaction tests against core contracts, using synthetic content."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

from core import charts, config, data, episodes, mascot, mission


PAGE = Path(__file__).resolve().parents[1] / "pages" / "1_Check_in.py"


@pytest.fixture
def screen(monkeypatch):
    state = {"now": datetime(2027, 4, 10, 8), "open": None, "pending": [],
             "calls": [], "speech": [], "chart_calls": []}
    indicators = {key: {"name": f"Indicator {key}", "unit": "example units",
                        "how_to_measure": f"Example instructions for {key}.",
                        "why_it_matters": "Synthetic test content."}
                  for key in ("x", "y", "_example")}
    problems = {"problem_a": {"name": "Example alert A", "confirm_wait_min": 5,
                              "triggers": [{"severity": "mild", "when": {"indicator": "x", "above": 10}}]}}
    state.update(indicators=indicators, problems=problems)
    monkeypatch.setattr(config, "load_indicators", lambda: indicators)
    monkeypatch.setattr(config, "load_problems", lambda: problems)
    monkeypatch.setattr(config, "load_environments", lambda: {"mars": {"name": "Mars"}, "iss": {"name": "ISS"}})
    monkeypatch.setattr(data, "get_open_episode", lambda astronaut: deepcopy(state["open"]))
    monkeypatch.setattr(data, "latest_values", lambda astronaut: {"x": 20, "y": 20})
    monkeypatch.setattr(data, "load_astronauts", lambda: pd.DataFrame({"id": ["a1", "a2"]}))
    monkeypatch.setattr(episodes, "get_pending", lambda astronaut: deepcopy(state["pending"]))
    monkeypatch.setattr(mission, "now", lambda: state["now"])
    monkeypatch.setattr(mascot, "say", lambda text, mood="neutral", size="large": state["speech"].append((text, mood, size)))
    original_chart = charts.indicator_chart

    def chart(astronaut, indicator, compact=False, environment=None):
        state["chart_calls"].append((astronaut, indicator, compact, environment))
        return original_chart(astronaut, indicator, compact, environment=environment)

    monkeypatch.setattr(charts, "indicator_chart", chart)

    def record(m, environment):
        state["calls"].append(("record", deepcopy(m), environment))
        return state["open"]

    def confirm(episode_id, m):
        state["calls"].append(("confirm", episode_id, deepcopy(m)))
        state["open"]["status"] = "active"
        return deepcopy(state["open"])

    def accept(astronaut, environment):
        state["calls"].append(("accept", astronaut, environment))
        if state["open"] is not None:
            return deepcopy(state["open"])
        if not state["pending"]:
            return None
        item = state["pending"].pop(0)
        opened(state)
        state["open"].update(problem=item["problem"], severity=item["severity"], environment=environment)
        state["open"]["trigger"] = {"indicator": item["indicator"], "measured_at": item["measured_at"]}
        return deepcopy(state["open"])

    monkeypatch.setattr(episodes, "on_new_measurement", record)
    monkeypatch.setattr(episodes, "confirm", confirm)
    monkeypatch.setattr(episodes, "accept_pending", accept)
    app = AppTest.from_file(str(PAGE))
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "mars"
    return app, state


def opened(state, status="pending_confirmation"):
    state["open"] = {"id": "ep-0001", "astronaut": "a1", "environment": "mars",
                     "status": status, "problem": "problem_a", "severity": "mild",
                     "trigger": {"indicator": "x", "measured_at": state["now"].isoformat()},
                     "opened_at": state["now"].isoformat()}


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_home_selection_is_required(screen):
    app, state = screen
    del app.session_state["environment"]
    app.run()
    assert not app.exception
    assert "Home" in app.warning[0].value
    assert not app.number_input
    assert state["speech"][-1][2] == "large"


def test_form_is_empty_unbounded_and_hides_fixtures(screen):
    app, state = screen
    app.run()
    assert not app.exception
    assert app.selectbox[0].options == ["Indicator x", "Indicator y"]
    assert app.number_input[0].value is None
    assert len(app.toggle) == 1
    assert state["chart_calls"][-1] == ("a1", "x", True, "mars")
    assert state["speech"][-1][2] == "small"
    assert state["calls"] == []


@pytest.mark.parametrize("status", [None, "pending_confirmation", "active"])
def test_chart_is_right_of_mascot_and_controls_are_below_both(screen, status):
    app, state = screen
    if status:
        opened(state, status)
    else:
        waiting(state)
    app.run()

    assert not app.exception
    columns = app.get("column")
    assert len(columns) == 2
    assert not columns[0].get("plotly_chart")
    assert len(columns[1].get("plotly_chart")) == 1
    assert all(not column.get("button") and not column.get("form") for column in columns)
    visual_row = next(index for index, node in app.main.children.items()
                      if hasattr(node, "children") and node.get("plotly_chart"))
    controls = [index for index, node in app.main.children.items() if node.type in ("button", "form")]
    assert controls and all(index > visual_row for index in controls)
    assert state["speech"][-1][2] == "small"


def test_records_only_on_submit_and_does_not_repeat_on_rerun(screen):
    app, state = screen
    app.run()
    app.number_input[0].set_value(20)
    assert state["calls"] == []
    button(app, "Record measurement").click().run()
    assert not app.exception
    assert app.success
    assert state["calls"] == [("record", {
        "timestamp": "2027-04-10T08:00:00", "astronaut": "a1", "indicator": "x",
        "value": 20, "unit": "example units", "phase": "mission", "source": "manual",
    }, "mars")]
    app.run()
    assert len(state["calls"]) == 1
    assert app.number_input[0].value is None
    assert not app.success


def test_empty_submission_is_not_sent_to_core(screen):
    app, state = screen
    app.run()
    button(app, "Record measurement").click().run()
    assert not app.exception
    assert state["calls"] == []
    assert "Enter a finite" in app.error[0].value


def test_selecting_indicator_changes_chart_and_submitted_unit(screen):
    app, state = screen
    state["indicators"]["y"]["unit"] = "other units"
    app.run()
    app.selectbox[0].select("y").run()
    assert state["chart_calls"][-1] == ("a1", "y", True, "mars")
    assert "other units" in app.number_input[0].label
    app.number_input[0].set_value(12)
    button(app, "Record measurement").click().run()
    assert state["calls"][0][1]["indicator"] == "y"


def test_pending_confirmation_locks_indicator_and_wait(screen):
    app, state = screen
    opened(state)
    app.run()
    assert not app.exception
    assert not app.selectbox
    assert app.number_input[0].disabled
    assert button(app, "Confirm repeat measurement").disabled
    assert button(app, "Simulate wait")
    assert "Repeat measurement" in app.subheader[0].value


def test_ready_repeat_calls_confirm_and_offers_protocol(screen):
    app, state = screen
    opened(state)
    state["now"] += timedelta(minutes=5)
    app.run()
    assert not app.number_input[0].disabled
    app.number_input[0].set_value(25)
    button(app, "Confirm repeat measurement").click().run()
    assert not app.exception
    assert state["calls"][0][0:2] == ("confirm", "ep-0001")
    assert state["calls"][0][2]["indicator"] == "x"
    assert button(app, "Open Protocol")


def test_dismissal_is_shown_and_manual_form_returns(screen, monkeypatch):
    app, state = screen
    opened(state)
    state["now"] += timedelta(minutes=5)

    def dismiss(*args):
        state["open"] = None
        return {"status": "dismissed"}

    monkeypatch.setattr(episodes, "confirm", dismiss)
    app.run()
    app.number_input[0].set_value(0)
    button(app, "Confirm repeat measurement").click().run()
    assert not app.exception
    assert "dismissed" in app.success[0].value
    assert app.selectbox


def test_core_error_is_displayed_without_success(screen, monkeypatch):
    app, state = screen

    def fail(*args):
        raise ValueError("Baseline data is unavailable.")

    monkeypatch.setattr(episodes, "on_new_measurement", fail)
    app.run()
    app.number_input[0].set_value(20)
    button(app, "Record measurement").click().run()
    assert not app.exception
    assert app.error[0].value == "Baseline data is unavailable."
    assert not app.success
    assert state["speech"][-1][0] == app.error[0].value
    app.run()
    assert not app.error
    assert state["speech"][-1][0] == "Choose an indicator and record a new measurement."


def test_simulate_wait_advances_real_clock_and_processes_revealed_measurements(screen, monkeypatch):
    app, state = screen
    opened(state)
    calls = []
    revealed = {"astronaut": "a2", "indicator": "y", "value": 20, "source": "simulated"}

    def advance(hours=24):
        calls.append(hours)
        state["now"] += timedelta(hours=hours)
        return [revealed]

    monkeypatch.setattr(mission, "advance", advance)
    app.run()
    button(app, "Simulate wait").click().run()
    assert not app.exception
    assert calls == [1]
    assert state["calls"] == [("record", revealed, "mars")]
    assert not app.number_input[0].disabled
    assert state["open"]["status"] == "pending_confirmation"


@pytest.mark.parametrize("clock_moved", [False, True])
def test_simulate_wait_reports_shared_detection_failure_without_confirming(screen, monkeypatch, clock_moved):
    app, state = screen
    opened(state)
    initial = deepcopy(state["open"])
    calls = []

    def fail(hours, environment):
        calls.append((hours, environment))
        if clock_moved:
            state["now"] += timedelta(hours=hours)
        raise OSError("Synthetic storage failure.")

    monkeypatch.setattr(mission, "advance_and_detect", fail)
    app.run()
    button(app, "Simulate wait").click().run()
    assert not app.exception
    assert calls == [(1, "mars")]
    assert "Synthetic storage failure" in app.error[0].value
    assert ("Mission time advanced, but detection could not finish" in app.error[0].value) is clock_moved
    assert not app.success
    assert state["open"] == initial
    assert state["calls"] == []


def test_stub_clock_cannot_bypass_confirmation_wait(screen, monkeypatch):
    app, state = screen
    opened(state)
    monkeypatch.setattr(mission, "advance", lambda hours=24: [])
    app.run()
    button(app, "Simulate wait").click().run()
    assert "did not advance" in app.error[0].value
    assert button(app, "Confirm repeat measurement").disabled


@pytest.mark.parametrize("field", ["how_to_measure", "why_it_matters", "unit"])
def test_unfinished_guidance_disables_submission(screen, field):
    app, state = screen
    state["indicators"]["x"][field] = "TODO_EDU"
    app.run()
    assert not app.exception
    assert app.warning
    assert button(app, "Record measurement").disabled
    assert state["calls"] == []


def test_unfinished_detection_rules_disable_submission(screen):
    app, state = screen
    state["problems"]["problem_a"]["triggers"][0]["when"]["above"] = "TODO_EDU"
    app.run()
    assert app.error
    assert button(app, "Record measurement").disabled


def test_pending_list_is_displayed_without_promoting_it(screen):
    app, state = screen
    state["pending"] = [{"problem": "problem_a", "severity": "severe", "measured_at": "2027-04-10T08:00:00"}]
    app.run()
    assert not app.exception
    assert app.dataframe[0].value.iloc[0]["Problem"] == "Example alert A"
    assert state["open"] is None
    assert state["calls"] == []


def test_active_protocol_navigation(screen, monkeypatch):
    import streamlit as st

    app, state = screen
    opened(state, status="active")
    destinations = []
    monkeypatch.setattr(st, "switch_page", destinations.append)
    app.run()
    button(app, "Open Protocol").click().run()
    assert destinations == ["pages/2_Protocol.py"]


def test_feedback_is_scoped_to_selected_astronaut_and_environment(screen):
    app, state = screen
    app.run()
    button(app, "Record measurement").click().run()
    assert app.error
    app.session_state["astronaut"] = "a2"
    app.run()
    assert not app.error


def waiting(state):
    state["pending"] = [{"problem": "problem_a", "severity": "severe", "indicator": "y",
                         "measured_at": (state["now"] - timedelta(hours=1)).isoformat()}]


def test_review_pending_starts_confirmation_and_does_not_repeat_on_rerun(screen):
    app, state = screen
    waiting(state)
    app.run()
    assert not button(app, "Review next alert").disabled
    button(app, "Review next alert").click().run()
    assert not app.exception
    assert state["calls"] == [("accept", "a1", "mars")]
    assert not app.selectbox
    assert state["chart_calls"][-1] == ("a1", "y", True, "mars")
    assert button(app, "Confirm repeat measurement").disabled
    assert state["open"]["status"] == "pending_confirmation"
    app.run()
    assert len(state["calls"]) == 1


@pytest.mark.parametrize("status", ["pending_confirmation", "active"])
def test_review_pending_is_unavailable_while_episode_is_open(screen, status):
    app, state = screen
    waiting(state)
    opened(state, status=status)
    app.run()
    assert all(b.label != "Review next alert" for b in app.button)


def test_review_pending_error_does_not_consume_alert(screen, monkeypatch):
    app, state = screen
    waiting(state)
    before = deepcopy(state["pending"])

    def fail(*args):
        raise ValueError("The pending alert cannot be accepted.")

    monkeypatch.setattr(episodes, "accept_pending", fail)
    app.run()
    button(app, "Review next alert").click().run()
    assert not app.exception
    assert app.error[0].value == "The pending alert cannot be accepted."
    assert state["pending"] == before
    assert state["open"] is None


def test_review_pending_requires_its_own_measurement_guidance(screen):
    app, state = screen
    waiting(state)
    state["indicators"]["y"]["how_to_measure"] = "TODO_EDU"
    app.run()
    assert button(app, "Review next alert").disabled
    assert not button(app, "Record measurement").disabled


def symptom_problem(state):
    problem = state["problems"]["problem_a"]
    del problem["triggers"]
    problem.update(symptoms={"a": {"name": "Synthetic symptom", "levels": [
        {"level": "watch", "when": {"indicator": "x", "above": 10}}]}},
        states=[{"state": "watch", "when": {"symptom": "a", "level_is": "watch"}}])


def test_symptom_only_configuration_enables_submission(screen):
    app, state = screen
    symptom_problem(state)
    app.run()
    assert not app.exception
    assert not button(app, "Record measurement").disabled
    app.number_input[0].set_value(20)
    button(app, "Record measurement").click().run()
    assert state["calls"][0][0] == "record"


def test_unfinished_symptom_configuration_blocks_submission(screen):
    app, state = screen
    symptom_problem(state)
    state["problems"]["problem_a"]["symptoms"]["a"]["levels"][0]["when"]["above"] = "TODO_EDU"
    app.run()
    assert button(app, "Record measurement").disabled


def test_symptom_state_and_detection_snapshot_are_displayed(screen):
    app, state = screen
    symptom_problem(state)
    opened(state)
    state["open"].update(severity="watch", symptoms={"a": "watch"})
    app.run()
    assert not app.exception
    assert any("Problem state: watch" in text.value for text in app.markdown)
    assert app.dataframe[0].value.iloc[0]["Symptom"] == "Synthetic symptom"


@pytest.mark.parametrize("status", [None, "pending_confirmation", "active"])
def test_incomplete_assessments_have_focused_warnings_and_brief_mascot_guidance(screen, monkeypatch, status):
    app, state = screen
    if status:
        opened(state, status)
    rules = state["problems"]["problem_a"]["triggers"]
    rules[0]["when"] = {"indicator": "x", "metric": "baseline_delta", "above": 5}
    rules.extend({"severity": "mild", "when": {"indicator": key, "above": 5}}
                 for key in ("unmeasured_a", "unmeasured_b", "unmeasured_c"))
    monkeypatch.setattr(data, "get_baseline", lambda *args: None)
    app.run()

    assert not app.exception
    assert len(app.warning) == 2
    assert "Cannot evaluate x: no valid pre-flight baseline" in app.warning[0].value
    assert app.warning[1].value == "3 other indicators have incomplete assessments."
    narration = state["speech"][-1][0]
    assert "incomplete" in narration
    assert "standard deviation" not in narration
    assert "unmeasured_" not in narration
    if status == "active":
        assert "open Protocol" in narration
    elif status == "pending_confirmation":
        assert "Repeat" in narration
    else:
        app.number_input[0].set_value(20)
        button(app, "Record measurement").click().run()
        assert not app.success
        assert app.warning[0].value == "Measurement recorded. Assessment is incomplete; see the warnings below."
        assert "standard deviation" not in state["speech"][-1][0]
