# AI-assisted: generated with Codex; human review pending.
"""Protocol execution against the example fixture with isolated storage."""
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock

import pytest

from core import protocol_engine as engine


@pytest.fixture
def episode():
    return {"id": "ep-test", "astronaut": "a1", "problem": "_example",
            "environment": "mars", "status": "active", "severity": "moderate",
            "severity_initial": "moderate", "current_node": None,
            "vars": {}, "answers": {}, "log": []}


@pytest.fixture(autouse=True)
def dependencies(monkeypatch):
    saved, measured = Mock(), Mock()
    monkeypatch.setattr(engine.data, "save_episode", saved)
    monkeypatch.setattr(engine.data, "add_measurement", measured)
    monkeypatch.setattr(engine.data, "latest_values", lambda astronaut: {"heart_rate": 60})
    monkeypatch.setattr(engine.mission, "now", lambda: datetime(2027, 4, 10, 8))
    monkeypatch.setattr(engine.triggers, "symptom_levels", Mock(return_value=dict(SYMPTOMS_NONE)))
    return saved, measured


SYMPTOMS_NONE = {"symptom_a": "not_present", "symptom_b": "not_present"}


def test_current_step_is_detached_and_uses_start(episode):
    before = deepcopy(episode)
    assert engine.current_step(episode)["id"] == "route"
    assert episode == before
    episode["current_node"] = "remeasure"
    step = engine.current_step(episode)
    assert step["unit"] == "units"
    assert step["text"] == "Measure the example indicator again."


def test_optional_measure_text(episode, monkeypatch):
    protocol = engine.load_protocol("_example")
    del protocol["nodes"]["remeasure"]["text"]
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "remeasure"
    assert engine.current_step(episode)["text"].startswith("Measure Example indicator")


def test_contact_requires_configured_delay(episode, monkeypatch):
    episode["current_node"] = "contact_now"
    with pytest.raises(ValueError, match="delay"):
        engine.current_step(episode)
    monkeypatch.setattr(engine, "load_environments", lambda: {"mars": {"comm_delay_min": 7}})
    assert engine.current_step(episode)["response_delay_min"] == 14


def test_initial_decision_uses_shared_evaluator_and_full_context(episode, monkeypatch):
    check = Mock(side_effect=[False, True])
    monkeypatch.setattr(engine.conditions, "check", check)
    updated = engine.submit(episode, None)
    assert updated["current_node"] == "intro_mars"
    ctx = check.call_args.args[1]
    assert ctx == {"astronaut": "a1", "environment": "mars", "severity": "moderate",
                   "vars": {}, "answers": {}, "latest": {"heart_rate": 60},
                   "var_indicators": {"value_after": "_example_indicator"}, "symptoms": SYMPTOMS_NONE}
    engine.triggers.symptom_levels.assert_called_with("_example", "a1", "mars")
    assert episode["current_node"] is None


def test_default_info_question_and_action(episode, monkeypatch):
    episode["environment"] = "iss"
    updated = engine.submit(episode, None)
    assert updated["current_node"] == "intro"
    updated = engine.submit(updated, {"action": "continue"})
    assert updated["current_node"] == "symptoms"
    updated = engine.submit(updated, {"answer": "no"})
    assert updated["answers"] == {"has_symptom": "no"}
    monkeypatch.setattr(engine.mission, "now", lambda: datetime(2027, 4, 10, 8, 1))
    updated = engine.submit(updated, {"action": "done"})
    assert updated["current_node"] == "remeasure"
    assert updated["log"][-1]["input"] == "done"


def test_cannot_route_and_contact_closure(episode, dependencies):
    episode["current_node"] = "do_action"
    updated = engine.submit(episode, {"action": "cannot"})
    assert updated["current_node"] == "contact_crew"
    updated = engine.submit(updated, {"action": "continue"})
    assert updated["status"] == updated["outcome"] == "monitoring"
    assert updated["closed_at"] == "2027-04-10T08:00:00"
    saved, _ = dependencies
    saved.reset_mock()
    assert engine.submit(updated, None) == updated
    saved.assert_not_called()


def test_question_escalates_and_hands_over(episode):
    episode["current_node"] = "symptoms"
    updated = engine.submit(episode, {"answer": "yes"})
    assert updated["severity"] == "severe"
    assert updated["severity_initial"] == "moderate"
    assert updated["current_node"] == "contact_now"
    updated = engine.submit(updated, {"action": "continue"})
    assert updated["status"] == "handed_over"


@pytest.mark.parametrize("matched_branch,outcome,severity", [
    (None, "resolved", "inactive"), (0, None, "severe"), (1, "monitoring", "moderate")])
def test_measurement_drives_decision(episode, monkeypatch, dependencies, matched_branch, outcome, severity):
    episode["current_node"] = "remeasure"
    calls = []

    def check(cond, ctx):
        calls.append(deepcopy(ctx))
        return matched_branch == len(calls) - 1

    monkeypatch.setattr(engine.conditions, "check", check)
    updated = engine.submit(episode, {"value": 8})
    assert updated["vars"] == {"value_after": 8}
    assert updated["severity"] == severity
    assert calls[0]["latest"]["_example_indicator"] == 8
    assert calls[0]["vars"]["value_after"] == 8
    if outcome:
        assert updated["status"] == updated["outcome"] == outcome
    else:
        assert updated["current_node"] == "contact_now"
    saved, measured = dependencies
    measured.assert_called_once_with({"timestamp": "2027-04-10T08:00:00", "astronaut": "a1",
                                      "indicator": "_example_indicator", "value": 8, "unit": "units",
                                      "phase": "mission", "source": "protocol"})
    saved.assert_called_once_with(updated)
    engine.submit(updated, None)
    measured.assert_called_once()


@pytest.mark.parametrize("node,user_input", [
    ("symptoms", {"answer": "unknown"}), ("intro", {"action": "done"}),
    ("do_action", {"action": "unknown"}), ("remeasure", {"value": True}),
    ("remeasure", {"value": float("nan")}), ("remeasure", {"value": float("inf")}),
    ("remeasure", {"value": "8"})])
def test_invalid_input_has_no_side_effects(episode, dependencies, node, user_input):
    episode["current_node"] = node
    before = deepcopy(episode)
    with pytest.raises(ValueError):
        engine.submit(episode, user_input)
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


def test_confirmation_cannot_run_protocol(episode, dependencies):
    episode["status"] = "pending_confirmation"
    with pytest.raises(ValueError, match="active"):
        engine.submit(episode, None)
    dependencies[0].assert_not_called()


def test_automatic_cycle_fails_before_persistence(episode, monkeypatch, dependencies):
    monkeypatch.setattr(engine, "load_protocol", lambda _: {
        "start": "loop", "nodes": {"loop": {"type": "decision", "branches": [], "default": "loop"}}})
    with pytest.raises(ValueError, match="cycle"):
        engine.submit(episode, None)
    dependencies[0].assert_not_called()


def test_interactive_loop_waits_for_another_response(episode, monkeypatch):
    monkeypatch.setattr(engine, "load_protocol", lambda _: {
        "start": "repeat", "nodes": {"repeat": {
            "type": "info", "text": "Example repeat.", "next": "repeat"}}})
    updated = engine.submit(episode, {"action": "continue"})
    assert updated["current_node"] == "repeat"
    assert len(updated["log"]) == 1


@pytest.mark.parametrize("seconds,allowed", [(0, False), (59, False), (60, True), (61, True)])
def test_action_wait_boundary_survives_reload(episode, monkeypatch, dependencies, seconds, allowed):
    from datetime import timedelta

    episode["current_node"] = "do_action"
    # An old opening/confirmation time must not satisfy this action's wait.
    episode["opened_at"] = "2027-04-09T08:00:00"
    updated = engine.submit(episode, None)
    assert updated["log"][-1] == {"at": "2027-04-10T08:00:00", "node": "do_action", "input": "wait_started"}
    before = deepcopy(updated)
    saved, measured = dependencies
    saved.reset_mock()
    monkeypatch.setattr(engine.mission, "now", lambda: datetime(2027, 4, 10, 8) + timedelta(seconds=seconds))
    assert engine.current_step(updated)["remaining_wait_min"] == pytest.approx(max(0, 1 - seconds / 60))
    if allowed:
        assert engine.submit(deepcopy(updated), {"action": "done"})["current_node"] == "remeasure"
        saved.assert_called_once()
    else:
        with pytest.raises(ValueError, match="wait is not complete"):
            engine.submit(deepcopy(updated), {"action": "done"})
        saved.assert_not_called()
    measured.assert_not_called()
    assert updated == before


def test_render_and_rerun_do_not_restart_action_wait(episode, monkeypatch):
    episode["current_node"] = "do_action"
    updated = engine.submit(episode, None)
    original_log = deepcopy(updated["log"])
    monkeypatch.setattr(engine.mission, "now", lambda: datetime(2027, 4, 10, 8, 0, 30))
    assert engine.current_step(updated)["remaining_wait_min"] == 0.5
    updated = engine.submit(updated, None)
    assert updated["log"] == original_log
    assert engine.current_step(updated)["remaining_wait_min"] == 0.5


def test_cannot_bypasses_active_wait(episode):
    episode["current_node"] = "do_action"
    updated = engine.submit(episode, None)
    assert engine.submit(updated, {"action": "cannot"})["current_node"] == "contact_crew"


@pytest.mark.parametrize("wait", ["TODO_EDU", -1, True, float("nan"), float("inf")])
def test_invalid_action_wait_is_rejected(episode, monkeypatch, dependencies, wait):
    protocol = engine.load_protocol("_example")
    protocol["nodes"]["do_action"]["wait_min"] = wait
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "do_action"
    with pytest.raises(ValueError, match="wait_min"):
        engine.current_step(episode)
    with pytest.raises(ValueError, match="wait_min"):
        engine.submit(episode, None)
    dependencies[0].assert_not_called()


def test_action_without_wait_continues_immediately(episode, monkeypatch):
    protocol = engine.load_protocol("_example")
    del protocol["nodes"]["do_action"]["wait_min"]
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "do_action"
    assert engine.current_step(episode)["remaining_wait_min"] == 0
    assert engine.submit(episode, {"action": "done"})["current_node"] == "remeasure"


def test_reentering_timed_action_starts_new_wait(episode, monkeypatch):
    protocol = engine.load_protocol("_example")
    protocol["nodes"]["do_action"]["next"] = "do_action"
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "do_action"
    updated = engine.submit(episode, None)
    monkeypatch.setattr(engine.mission, "now", lambda: datetime(2027, 4, 10, 8, 1))
    updated = engine.submit(updated, {"action": "done"})
    assert engine.current_step(updated)["remaining_wait_min"] == 1
    with pytest.raises(ValueError, match="wait is not complete"):
        engine.submit(updated, {"action": "done"})


@pytest.mark.parametrize("problem", ["problem_1", "problem_2"])
def test_placeholder_protocol_cannot_close_episode(episode, dependencies, problem):
    episode["problem"] = problem
    before = deepcopy(episode)
    with pytest.raises(ValueError, match="TODO"):
        engine.submit(episode, None)
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


def test_todo_end_prevents_measurement_and_severity_writes(episode, monkeypatch, dependencies):
    protocol = engine.load_protocol("_example")
    protocol["nodes"]["done"]["text"] = "TODO_EDU: write the final instructions."
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "remeasure"
    before = deepcopy(episode)
    with pytest.raises(ValueError, match="TODO"):
        engine.submit(episode, {"value": 8})
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


@pytest.mark.parametrize("response", [None, {"action": "continue"}])
def test_todo_step_cannot_be_displayed_or_submitted(episode, monkeypatch, dependencies, response):
    protocol = engine.load_protocol("_example")
    protocol["nodes"]["intro"]["text"] = "TODO_GONZALO: write this step."
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    episode["current_node"] = "intro"
    before = deepcopy(episode)
    with pytest.raises(ValueError, match="TODO"):
        engine.current_step(episode)
    with pytest.raises(ValueError, match="TODO"):
        engine.submit(episode, response)
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


def test_todo_in_nested_branch_is_rejected_before_execution(episode, monkeypatch, dependencies):
    protocol = engine.load_protocol("_example")
    protocol["nodes"]["check"]["branches"][0]["if"]["above"] = "TODO_EDU"
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    before = deepcopy(episode)
    with pytest.raises(ValueError, match="TODO"):
        engine.submit(episode, None)
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


# Symptom-based problems (AGENTS.md 5.3 and 9): synthetic protocols, real condition evaluator.
def symptom_protocol(start: str = "route") -> dict:
    return {"problem": "_example", "start": start, "nodes": {
        "measure": {"type": "measure", "indicator": "_example_indicator", "save_as": "value_after",
                    "next": "route"},
        "route": {"type": "decision", "default": "keep_watching", "branches": [
            {"if": {"symptom": "symptom_a", "level_at_least": "concern"}, "next": "escalate"}]},
        "escalate": {"type": "set_severity", "severity": "medical_urgency", "next": "handover"},
        "handover": {"type": "end", "outcome": "handed_over", "text": "Synthetic handover."},
        "keep_watching": {"type": "end", "outcome": "monitoring", "text": "Synthetic monitoring."}}}


@pytest.mark.parametrize("level,severity,outcome", [
    ("concern", "medical_urgency", "handed_over"), ("watch", "watch", "monitoring"),
    ("not_present", "watch", "monitoring")])
def test_decision_branches_on_symptom_level_and_sets_problem_state(episode, monkeypatch, level, severity, outcome):
    monkeypatch.setattr(engine, "load_protocol", lambda _: symptom_protocol())
    monkeypatch.setattr(engine.triggers, "symptom_levels", Mock(return_value={**SYMPTOMS_NONE, "symptom_a": level}))
    episode.update(severity="watch", severity_initial="watch")
    updated = engine.submit(episode, None)
    assert (updated["severity"], updated["status"], updated["outcome"]) == (severity, outcome, outcome)
    assert updated["severity_initial"] == "watch"


def test_symptom_levels_are_recomputed_after_a_new_measurement(episode, monkeypatch, dependencies):
    saved, measured = dependencies
    monkeypatch.setattr(engine, "load_protocol", lambda _: symptom_protocol(start="measure"))

    def levels(problem, astronaut, environment):
        # The reading must already be stored, since symptom_levels reads the latest values.
        assert measured.call_count == 1
        return {**SYMPTOMS_NONE, "symptom_a": "concern"}

    monkeypatch.setattr(engine.triggers, "symptom_levels", Mock(side_effect=levels))
    episode.update(severity="watch", severity_initial="watch")
    updated = engine.submit(episode, {"value": 25})
    engine.triggers.symptom_levels.assert_called_once_with("_example", "a1", "mars")
    assert updated["severity"] == "medical_urgency"
    saved.assert_called_once_with(updated)


@pytest.mark.parametrize("problem,severity", [
    ({"triggers": []}, "medical_urgency"), ({"symptoms": {}, "states": []}, "severe")])
def test_set_severity_uses_the_problem_vocabulary(episode, monkeypatch, dependencies, problem, severity):
    protocol = symptom_protocol(start="escalate")
    protocol["nodes"]["escalate"]["severity"] = severity
    monkeypatch.setattr(engine, "load_protocol", lambda _: protocol)
    monkeypatch.setattr(engine, "load_problems", lambda include_examples=False: {"_example": problem})
    before = deepcopy(episode)
    with pytest.raises(ValueError, match="severity"):
        engine.submit(episode, None)
    assert episode == before
    for mock in dependencies:
        mock.assert_not_called()


def test_legacy_problem_decisions_get_no_symptoms(episode, monkeypatch):
    check = Mock(return_value=False)
    monkeypatch.setattr(engine.conditions, "check", check)
    monkeypatch.setattr(engine, "load_problems", lambda include_examples=False: {"_example": {"triggers": []}})
    engine.submit(episode, None)
    assert "symptoms" not in check.call_args.args[1]
    engine.triggers.symptom_levels.assert_not_called()
