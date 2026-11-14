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
    # Protocol readings are stored through detection (episodes.on_new_measurement).
    monkeypatch.setattr(engine.episodes, "on_new_measurement", measured)
    monkeypatch.setattr(engine.data, "add_measurement", Mock(side_effect=AssertionError("use detection")))
    monkeypatch.setattr(engine.data, "get_open_episode", lambda astronaut: {"id": "ep-test", "status": "active"})
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


@pytest.mark.parametrize("delay", ["TODO_EDU", None, -1, float("nan"), True])
def test_contact_requires_configured_delay(episode, monkeypatch, delay):
    # Fixture environments, so the test does not depend on the real values in config/.
    monkeypatch.setattr(engine, "load_environments", lambda: {"mars": {"comm_delay_min": delay}})
    episode["current_node"] = "contact_now"
    with pytest.raises(ValueError, match="delay"):
        engine.current_step(episode)


@pytest.mark.parametrize("environment,delay,expected", [("mars", 7, 14), ("iss", 0, 0), ("moon", 1.27 / 60, 2 * 1.27 / 60)])
def test_contact_shows_round_trip_delay(episode, monkeypatch, environment, delay, expected):
    monkeypatch.setattr(engine, "load_environments", lambda: {environment: {"comm_delay_min": delay}})
    episode.update(current_node="contact_now", environment=environment)
    assert engine.current_step(episode)["response_delay_min"] == expected


@pytest.mark.parametrize("delay", [22, "TODO_EDU", None])
def test_local_medical_officer_contact_has_no_earth_delay(episode, monkeypatch, delay):
    # #141: on-board contact, so no signal delay, and a missing Earth delay does not block it.
    monkeypatch.setattr(engine, "load_environments", lambda: {"mars": {"comm_delay_min": delay}})
    episode["current_node"] = "contact_crew"
    assert "response_delay_min" not in engine.current_step(episode)


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
                                      "phase": "mission", "source": "protocol"}, "mars")
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


def test_placeholder_protocol_cannot_close_episode(episode, monkeypatch, dependencies):
    # Same shape as an unwritten protocol, built here so no test depends on real problem ids.
    placeholder = {"problem": "_example", "start": "todo", "nodes": {"todo": {
        "type": "end", "outcome": "resolved", "text": "TODO_EDU: write this protocol."}}}
    monkeypatch.setattr(engine, "load_protocol", lambda _: deepcopy(placeholder))
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


# Flowchart DOT for the Protocol page (#69), from the _example fixture.
def node_line(dot: str, node_id: str) -> str:
    return next(line for line in dot.splitlines() if line.startswith(f'"{node_id}" ['))


def edge_line(dot: str, source: str, target: str) -> str:
    return next(line for line in dot.splitlines() if line.startswith(f'"{source}" -> "{target}" '))


def test_flowchart_highlights_current_and_marks_visited_route(episode):
    episode.update(current_node="symptoms", log=[{"at": "t", "node": "route", "input": None},
                                                {"at": "t", "node": "intro_mars", "input": "continue"}])
    dot = engine.flowchart_dot(episode, whole=True)
    assert 'fillcolor="#fef3c7"' in node_line(dot, "symptoms") and "penwidth=2.5" in node_line(dot, "symptoms")
    for visited in ("route", "intro_mars"):
        assert 'fillcolor="#dcfce7"' in node_line(dot, visited)
    assert 'fillcolor="#f1f5f9"' in node_line(dot, "intro")
    assert "penwidth=2.5" in edge_line(dot, "route", "intro_mars")
    assert "penwidth=2.5" in edge_line(dot, "intro_mars", "symptoms")
    assert "penwidth=1" in edge_line(dot, "route", "intro")


def test_flowchart_starts_at_the_start_node_and_draws_the_whole_protocol(episode):
    protocol = engine.load_protocol("_example")
    dot = engine.flowchart_dot(episode, whole=True)
    assert 'fillcolor="#fef3c7"' in node_line(dot, protocol["start"])
    for node_id in protocol["nodes"]:
        node_line(dot, node_id)
    assert dot.count(" -> ") == sum(len(engine._edges(node)) for node in protocol["nodes"].values())


def test_flowchart_labels_are_short_and_readable(episode):
    dot = engine.flowchart_dot(episode, whole=True)
    assert 'label="Check", shape=diamond' in node_line(dot, "route")
    assert 'label="Contact flight\\nsurgeon"' in node_line(dot, "contact_now")
    assert 'label="End: Handed over"' in node_line(dot, "handed_over")
    assert 'label="Severity: Severe"' in node_line(dot, "escalate")
    expected = {("route", "contact_now"): "Severe or worse", ("route", "intro_mars"): "Mars",
                ("route", "intro"): "Otherwise", ("symptoms", "do_action"): "No",
                ("do_action", "contact_crew"): "I can't", ("check", "escalate"): "Value > 20"}
    for (source, target), label in expected.items():
        assert f'[label="{label}"' in edge_line(dot, source, target)
    full_text = engine.load_protocol("_example")["nodes"]["intro_mars"]["text"]
    assert full_text not in dot
    assert "…" in dot and "\\u2026" not in dot


def test_flowchart_ignores_wait_entries_and_marks_a_finished_protocol(episode):
    episode.update(status="handed_over", current_node="handed_over", log=[
        {"at": "t", "node": "do_action", "input": "wait_started"},
        {"at": "t", "node": "do_action", "input": "cannot"},
        {"at": "t", "node": "contact_crew", "input": "continue"},
        {"at": "t", "node": "handed_over", "input": None}])
    dot = engine.flowchart_dot(episode)
    assert '"do_action" -> "do_action"' not in dot
    assert "penwidth=2.5" in edge_line(dot, "do_action", "contact_crew")
    assert 'fillcolor="#fef3c7"' in node_line(dot, "handed_over")


def drawn_nodes(dot: str) -> set[str]:
    return {line.split('"')[1] for line in dot.splitlines() if line.startswith('"') and " -> " not in line}


def test_focused_flowchart_shows_recent_steps_current_and_where_options_lead(episode):
    # Visited: route > intro_mars > symptoms > do_action > remeasure; current: contact_crew.
    path = ["route", "intro_mars", "symptoms", "do_action", "remeasure"]
    episode.update(current_node="contact_crew", log=[{"at": "t", "node": n, "input": "x"} for n in path])
    dot = engine.flowchart_dot(episode)
    # Last three visited steps, the current one and its exit; earlier steps collapse into one box.
    assert drawn_nodes(dot) == {"_earlier", "symptoms", "do_action", "remeasure", "contact_crew", "monitor"}
    assert 'label="… 2 earlier steps"' in dot
    assert '"_earlier" -> "symptoms"' in dot
    assert "fontsize=16" in dot


def test_focused_flowchart_follows_automatic_nodes_and_hides_unrelated_edges(episode):
    episode.update(current_node="symptoms", log=[{"at": "t", "node": "route", "input": None},
                                                {"at": "t", "node": "intro_mars", "input": "continue"}])
    dot = engine.flowchart_dot(episode)
    # "yes" leads through set_severity (automatic) to contact_now, so both are shown.
    assert drawn_nodes(dot) == {"route", "intro_mars", "symptoms", "escalate", "contact_now", "do_action"}
    assert "_earlier" not in dot
    assert '[label="Yes"' in edge_line(dot, "symptoms", "escalate")
    assert edge_line(dot, "escalate", "contact_now")
    # A visited node's other branches are not drawn, even if their target is on screen.
    assert '"route" -> "contact_now"' not in dot
    assert "penwidth=2.5" in edge_line(dot, "route", "intro_mars")


@pytest.mark.parametrize("cond,label", [
    ({"any": [{"symptom": "a", "level_is": "concern"}, {"symptom": "b", "level_is": "concern"}]}, "Any finding: Concern"),
    ({"all": [{"symptom": "a", "level_at_least": "watch"}, {"symptom": "b", "level_at_least": "watch"}]}, "All findings: Watch"),
    ({"count_at_least": 2, "of": [{"symptom": "a", "level_is": "concern"}, {"symptom": "b", "level_is": "concern"}]}, "2+ findings: Concern"),
    ({"any": [{"symptom": "a", "level_is": "concern"}, {"environment_in": ["mars"]}]}, "Condition met")])
def test_symptom_group_branches_get_short_labels(cond, label):
    assert engine._condition_label(cond) == label
