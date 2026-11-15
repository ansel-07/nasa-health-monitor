# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Check-in interaction tests against core contracts, using synthetic content."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

from core import activity, charts, config, data, episodes, mascot, mission, triggers


PAGE = Path(__file__).resolve().parents[1] / "pages" / "1_Check_in.py"


@pytest.fixture
def screen(monkeypatch):
    state = {"now": datetime(2027, 4, 10, 8), "open": None, "pending": [],
             "calls": [], "speech": [], "chart_calls": [], "completions": [], "destinations": []}
    indicators = {key: {"name": f"Indicator {key}", "unit": "example units",
                        "how_to_measure": f"Example instructions for {key}.",
                        "why_it_matters": "Synthetic test content."}
                  for key in ("x", "y", "_example")}
    problems = {"problem_a": {"name": "Example alert A", "confirm_wait_min": 5,
                              "triggers": [{"severity": "mild", "when": {"indicator": "x", "above": 10}}]}}
    state.update(indicators=indicators, problems=problems)
    state["checkins"] = {key: {"name": f"Check {key}", "indicators": [key], "bar_full_hours": 24}
                         for key in ("x", "y")}
    monkeypatch.setattr(config, "load_checkins", lambda: state["checkins"])
    monkeypatch.setattr(activity, "bar_level", lambda *args: 0)
    monkeypatch.setattr(activity, "complete", lambda *args: state["completions"].append(args))
    import streamlit as st

    def switch(destination):
        state["destinations"].append(destination)
        st.rerun()

    monkeypatch.setattr(st, "switch_page", switch)


    state.update(subjective_config={"issues": {}}, issue_records={}, issue_calls=[])
    monkeypatch.setattr(config, "load_subjective_issues", lambda **kwargs: state["subjective_config"])
    monkeypatch.setattr(activity, "active_issues", lambda astronaut: deepcopy(state["issue_records"].get(astronaut, [])))

    def report_issues(astronaut, issue_ids, source):
        state["issue_calls"].append(("report", astronaut, issue_ids, source))
        active = state["issue_records"].setdefault(astronaut, [])
        for issue_id in issue_ids:
            if not any(item["issue"] == issue_id for item in active):
                active.append({"issue": issue_id, "since": state["now"].isoformat(), "persistent": False})

    def resolve(astronaut, issue_id):
        state["issue_calls"].append(("resolve", astronaut, issue_id))
        state["issue_records"][astronaut] = [item for item in state["issue_records"][astronaut]
                                              if item["issue"] != issue_id]

    monkeypatch.setattr(activity, "report_issues", report_issues)
    monkeypatch.setattr(activity, "resolve_issue", resolve)
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
    app.session_state["check_in_selected:a1:mars"] = "x"
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
    assert state["speech"][-1][2] == "medium"


def test_form_is_empty_unbounded_and_hides_fixtures(screen):
    app, state = screen
    app.run()
    assert not app.exception
    assert not app.selectbox      # one chart per indicator of the check-in, no indicator picker
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
    # Mascot | visual; the data tiles under the chart add three columns inside the visual one.
    columns = app.get("column")[:2]
    assert len(columns) == 2 and len(app.get("column")) in (2, 5)
    assert len(columns[1].get("metric")) in (0, 3)
    assert not columns[0].get("plotly_chart")
    assert len(columns[1].get("plotly_chart")) == 1
    assert all(not column.get("button") and not column.get("form") for column in columns)
    visual_row = next(index for index, node in app.main.children.items()
                      if hasattr(node, "children") and node.get("plotly_chart"))
    controls = [index for index, node in app.main.children.items() if node.type in ("button", "form")
                and getattr(node, "label", "") != "Back to check-ins"]
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
    button(app, "Back to check-ins").click().run()
    button(app, "Check y").click().run()
    assert state["chart_calls"][-1] == ("a1", "y", True, "mars")
    assert "other units" in app.number_input[0].label
    app.number_input[0].set_value(12)
    button(app, "Record measurement").click().run()
    assert state["calls"][0][1]["indicator"] == "y"


@pytest.mark.parametrize("now,wait,expected", [
    ("2027-04-02T00:00:00", 10, "Repeat after 00:10, mission day 2 (10 minutes remaining)."),
    ("2027-04-02T00:00:00", 1, "Repeat after 00:01, mission day 2 (1 minute remaining)."),
    ("2027-04-02T23:55:00", 10, "Repeat after 00:05, mission day 3 (10 minutes remaining)."),
    ("2027-04-02T00:00:00", 0.5, "Repeat after 00:00, mission day 2 (1 minute remaining)."),
])
def test_pending_confirmation_shows_readable_due_time(screen, monkeypatch, now, wait, expected):
    app, state = screen
    monkeypatch.setattr(config, "load_mission", lambda: {"start": "2027-04-01T00:00:00"})
    state["now"] = datetime.fromisoformat(now)
    state["problems"]["problem_a"]["confirm_wait_min"] = wait
    opened(state)
    app.run()
    assert not app.exception
    assert expected in [item.value for item in app.info]
    assert button(app, "Confirm repeat measurement").disabled
    assert state["calls"] == []


def test_pending_confirmation_locks_indicator_and_wait(screen):
    app, state = screen
    opened(state)
    app.run()
    assert not app.exception
    assert not app.selectbox
    assert app.number_input[0].disabled
    assert button(app, "Confirm repeat measurement").disabled
    assert button(app, "Simulate wait")
    assert any("Repeat measurement" in item.value for item in app.subheader)


@pytest.mark.parametrize("status,expected_environment", [
    ("pending_confirmation", "mars"), ("active", "iss"), (None, "iss"),
])
def test_chart_and_assessment_share_environment_after_home_selection_changes(screen, monkeypatch, status, expected_environment):
    app, state = screen
    if status:
        opened(state, status)
    app.session_state["environment"] = "iss"
    app.session_state["check_in_selected:a1:iss"] = "x"
    assessment_environments = []
    original_assessment = triggers.assessment_issues

    def assessment(problems, astronaut, indicator, environment):
        assessment_environments.append(environment)
        return original_assessment(problems, astronaut, indicator, environment)

    monkeypatch.setattr(triggers, "assessment_issues", assessment)
    before = deepcopy(state["open"])
    app.run()
    assert not app.exception
    assert state["chart_calls"][-1] == ("a1", "x", True, expected_environment)
    assert assessment_environments == [expected_environment]
    assert state["open"] == before
    if status:
        assert any("original environment: Mars" in item.value for item in app.info)


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
    assert state["destinations"] == ["pages/2_Protocol.py"]
    assert state["completions"] == [("a1", "check_in", "x")]


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
    assert button(app, "Record measurement")     # the manual form is back


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
    assert state["speech"][-1][0] == "Record the measurements of this check-in."


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


@pytest.mark.parametrize("status", ["pending_confirmation", "active"])
def test_symptom_state_and_detection_snapshot_are_displayed(screen, status):
    app, state = screen
    symptom_problem(state)
    opened(state, status)
    state["open"].update(severity="watch", symptoms={"a": "watch", "older": "concern", "absent": "not_present"})
    before = deepcopy(state["open"])
    app.run()
    assert not app.exception
    assert any("Problem state: watch" in text.value for text in app.markdown)
    assert not app.dataframe
    assert app.table[0].value.to_dict("records") == [
        {"Symptom": "Synthetic symptom", "Level": "watch"},
        {"Symptom": "older", "Level": "concern"},
        {"Symptom": "absent", "Level": "not_present"},
    ]
    assert state["open"] == before


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


def test_list_cards_use_configured_groups_and_allow_full_bars(screen, monkeypatch):
    app, state = screen
    app.session_state['check_in_selected:a1:mars'] = None
    calls = []
    monkeypatch.setattr(activity, 'bar_level', lambda *args: calls.append(args) or 100)
    app.run()
    assert not app.exception
    assert not app.number_input
    assert [item.value for item in app.get('progress')] == [100, 100]
    assert calls == [('a1', 'check_in', 'x'), ('a1', 'check_in', 'y')]
    assert state['speech'][-1][2] == 'medium'     # list: compact mascot line, cards below
    assert not button(app, 'Check y').disabled
    button(app, 'Check y').click().run()
    assert state['chart_calls'][-1][1] == 'y'
    button(app, 'Back to check-ins').click().run()
    assert not app.number_input
    assert state['calls'] == []


def test_empty_checkin_list_is_honest(screen):
    app, state = screen
    state['checkins'].clear()
    app.run()
    assert not app.exception
    assert any('No check-ins' in item.value for item in app.info)
    assert not app.number_input


def test_back_preserves_confirmation_and_can_resume(screen):
    app, state = screen
    opened(state)
    before = deepcopy(state['open'])
    app.run()
    button(app, 'Back to check-ins').click().run()
    assert not app.number_input
    assert state['open'] == before
    button(app, 'Continue repeat measurement').click().run()
    assert button(app, 'Confirm repeat measurement').disabled
    assert state['calls'] == []


def group_xy(state):
    state['checkins']['x']['indicators'] = ['x', 'y']
    state['checkins'].pop('y')


def test_group_requires_all_values_before_recording_any(screen):
    app, state = screen
    group_xy(state)
    app.run()
    assert len(app.number_input) == 2
    app.number_input[0].set_value(20)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert state['calls'] == state['completions'] == []
    assert 'every indicator' in app.error[0].value


def test_group_saves_independent_values_and_completes_once(screen):
    app, state = screen
    group_xy(state)
    state['indicators']['y']['unit'] = 'second units'
    app.run()
    app.number_input[0].set_value(2)
    app.number_input[1].set_value(3)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert [(item[1]['indicator'], item[1]['value'], item[1]['unit']) for item in state['calls']] == [
        ('x', 2, 'example units'), ('y', 3, 'second units')]
    assert state['completions'] == [('a1', 'check_in', 'x')]
    app.run()
    button(app, 'Back to check-ins').click().run()
    assert len(state['calls']) == 2 and len(state['completions']) == 1


def test_group_retries_only_remaining_values_after_partial_failure(screen, monkeypatch):
    app, state = screen
    group_xy(state)
    original = episodes.on_new_measurement
    fail = [True]

    def record(m, environment):
        if m['indicator'] == 'y' and fail[0]:
            fail[0] = False
            raise OSError('Synthetic storage failure')
        result = original(m, environment)
        if m['indicator'] == 'x':
            opened(state)
            return state['open']
        return result

    monkeypatch.setattr(episodes, 'on_new_measurement', record)
    app.run()
    app.number_input[0].set_value(20)
    app.number_input[1].set_value(30)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert len(state['calls']) == 1 and not state['completions']
    assert len(app.number_input) == 2
    assert all(item.label != 'Continue repeat measurement' for item in app.button)
    state['now'] += timedelta(minutes=1)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert [item[1]['indicator'] for item in state['calls']] == ['x', 'y']
    assert state['calls'][0][1]['timestamp'] == state['calls'][1][1]['timestamp']
    assert not state['completions']
    assert len(app.number_input) == 1
    assert button(app, 'Confirm repeat measurement').disabled


def test_completion_retry_does_not_record_values_again(screen, monkeypatch):
    app, state = screen
    attempts = [0]

    def complete(*args):
        attempts[0] += 1
        if attempts[0] == 1:
            raise OSError('Synthetic completion failure')
        state['completions'].append(args)

    monkeypatch.setattr(activity, 'complete', complete)
    app.run()
    app.number_input[0].set_value(2)
    button(app, 'Record measurement').click().run()
    assert not app.exception
    assert len(state['calls']) == 1
    assert button(app, 'Record measurement').disabled
    button(app, 'Finish check-in').click().run()
    assert not app.exception
    assert len(state['calls']) == len(state['completions']) == 1


def subjective_fixture(state):
    state['subjective_config']['issues'] = {
        'issue_a': {'label': 'Synthetic issue A', 'check_ins': ['x']},
        'issue_b': {'label': 'Synthetic issue B', 'check_ins': ['y']},
    }


@pytest.mark.parametrize('detail,source', [(False, 'check_in_list'), (True, 'check_in_detail')])
def test_subjective_issues_save_only_on_explicit_submit(screen, detail, source):
    app, state = screen
    subjective_fixture(state)
    if not detail:
        app.session_state['check_in_selected:a1:mars'] = None
    app.run()
    assert not app.exception
    app.multiselect[0].set_value(['issue_a', 'issue_b'])
    assert state['issue_calls'] == []
    button(app, 'Save issues').click().run()
    assert not app.exception
    assert state['issue_calls'] == [('report', 'a1', ['issue_a', 'issue_b'], source)]
    assert state['calls'] == [] and state['open'] is None
    app.run()
    assert len(state['issue_calls']) == 1


def test_subjective_panel_follows_all_list_cards(screen):
    app, state = screen
    subjective_fixture(state)
    app.session_state['check_in_selected:a1:mars'] = None
    app.run()
    card_row = next(index for index, node in app.main.children.items()
                    if hasattr(node, 'children') and node.get('progress'))
    issue_panel = next(index for index, node in app.main.children.items()
                       if getattr(node, 'label', '') == 'Subjective issues')
    assert issue_panel > card_row


def test_deselecting_saved_issue_explicitly_resolves_it(screen):
    app, state = screen
    subjective_fixture(state)
    state['issue_records']['a1'] = [{'issue': 'issue_a', 'since': '2027-04-10T08:00:00', 'persistent': True}]
    app.run()
    assert app.multiselect[0].value == ['issue_a']
    assert state['issue_calls'] == []
    app.multiselect[0].set_value([])
    button(app, 'Save issues').click().run()
    assert not app.exception
    assert state['issue_calls'] == [('resolve', 'a1', 'issue_a')]
    assert app.multiselect[0].value == []


def test_subjective_issue_selection_is_separate_for_each_astronaut(screen):
    app, state = screen
    subjective_fixture(state)
    state['issue_records']['a1'] = [{'issue': 'issue_a', 'since': '2027-04-10T08:00:00', 'persistent': False}]
    app.run()
    assert app.multiselect[0].value == ['issue_a']
    app.session_state['astronaut'] = 'a2'
    app.run()
    assert not app.exception
    assert app.multiselect[0].value == []
    assert state['issue_calls'] == []


def test_unconfigured_subjective_issues_show_empty_state(screen):
    app, state = screen
    app.run()
    assert not app.multiselect
    assert any('Subjective issues are not configured' in item.value for item in app.info)
    assert state['issue_calls'] == []


def test_subjective_report_failure_preserves_existing_issue(screen, monkeypatch):
    app, state = screen
    subjective_fixture(state)
    state['issue_records']['a1'] = [{'issue': 'issue_a', 'since': '2027-04-10T08:00:00', 'persistent': False}]

    def fail(*args, **kwargs):
        raise OSError('Synthetic issue storage failure')

    monkeypatch.setattr(activity, 'report_issues', fail)
    app.run()
    app.multiselect[0].set_value(['issue_b'])
    button(app, 'Save issues').click().run()
    assert not app.exception
    assert any('could not be fully saved' in item.value for item in app.error)
    assert state['issue_calls'] == []
    assert state['issue_records']['a1'][0]['issue'] == 'issue_a'


def test_detail_shows_one_chart_per_indicator_of_the_check_in(screen):
    """docs/FRONTEND_MASCOT_LAYOUT.md 4.2: the visual is every indicator's compact chart, stacked."""
    app, state = screen
    state["checkins"]["x"]["indicators"] = ["x", "y"]
    app.run()
    assert not app.exception
    assert [call[1] for call in state["chart_calls"][-2:]] == ["x", "y"]
    assert len(app.number_input) == 2
