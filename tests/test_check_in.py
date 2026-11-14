# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Check-in interaction tests against core contracts, using synthetic content."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest
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


def test_records_only_on_submit_and_does_not_repeat_on_rerun(screen):
    app, state = screen
    app.run()
    app.number_input[0].set_value(20)
    assert state["calls"] == []
    button(app, "Record measurement").click().run()
    assert not app.exception
    assert state["calls"] == [("record", {
        "timestamp": "2027-04-10T08:00:00", "astronaut": "a1", "indicator": "x",
        "value": 20, "unit": "example units", "phase": "mission", "source": "manual",
    }, "mars")]
    app.run()
    assert len(state["calls"]) == 1
    assert app.number_input[0].value is None
    assert app.success


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
