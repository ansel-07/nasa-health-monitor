# AI-assisted: generated with Codex; human review pending.
"""Manual sandbox journeys and restoration of production dependencies."""
import pytest
from streamlit.testing.v1 import AppTest

from core import conditions, config, data, mission


def button(app, label):
    return next(item for item in app.button if item.label == label)


def select(app, label):
    return next(item for item in app.selectbox if item.label == label)


def preview():
    app = AppTest.from_file("../scripts/preview_protocol.py").run()
    assert not app.exception
    return app


@pytest.mark.parametrize("value,outcome", [(8, "resolved"), (15, "monitoring"), (25, "handed_over")])
def test_manual_measurement_routes_and_isolation(value, outcome):
    originals = (data.save_episode, data.add_measurement, conditions.check, config.load_problems, mission.now)
    app = preview()
    select(app, "Scenario").set_value("Measurement branches")
    button(app, "Load / restart scenario").click().run()
    next(item for item in app.number_input if item.label == "Measurement (units)").set_value(value)
    button(app, "Save measurement").click().run()
    assert not app.exception
    if outcome == "handed_over":
        button(app, "Continue").click().run()
    state = app.session_state["protocol_sandbox"]
    assert state["episode"]["status"] == outcome
    assert len(state["measurements"]) == 1
    assert app.success
    assert originals == (data.save_episode, data.add_measurement, conditions.check, config.load_problems, mission.now)


def test_manual_full_journey_wait_and_reset():
    app = preview()
    button(app, "Continue").click().run()
    button(app, "No").click().run()
    assert button(app, "Done").disabled
    button(app, "Advance 1 minute(s)").click().run()
    assert not app.exception
    assert not button(app, "Done").disabled
    button(app, "Done").click().run()
    assert any(item.label == "Measurement (units)" for item in app.number_input)
    button(app, "Load / restart scenario").click().run()
    assert not app.exception
    state = app.session_state["protocol_sandbox"]
    assert state["episode"]["current_node"] == "intro"
    assert state["measurements"] == []


def test_manual_empty_and_confirmation_scenarios():
    app = preview()
    select(app, "Scenario").set_value("Pending confirmation")
    button(app, "Load / restart scenario").click().run()
    assert not app.exception
    assert not any(item.label == "Continue" for item in app.button)
    assert app.session_state["protocol_sandbox"]["episode"]["status"] == "pending_confirmation"
    select(app, "Scenario").set_value("No episode")
    button(app, "Load / restart scenario").click().run()
    assert not app.exception
    assert app.session_state["protocol_sandbox"]["episode"] is None


def test_visualizer_tracks_live_current_node_and_route():
    app = preview()
    graph = app.get("graphviz_chart")[-1].proto.spec
    assert "CURRENT | intro" in graph
    assert '"route" -> "intro" [label="Otherwise", color="#15803d", penwidth=3]' in graph
    button(app, "Continue").click().run()
    assert not app.exception
    graph = app.get("graphviz_chart")[-1].proto.spec
    assert "CURRENT | symptoms" in graph
    assert "VISITED | intro" in graph
    assert '"intro" -> "symptoms" [label="Continue", color="#15803d", penwidth=3]' in graph
    select(app, "Inspect node").set_value("check").run()
    assert not app.exception


def test_visualizer_edges_come_from_all_runtime_transitions():
    from copy import deepcopy
    from scripts.preview_protocol import fixture_protocol, protocol_dot, protocol_edges

    protocol = fixture_protocol()
    before = deepcopy(protocol)
    edges = protocol_edges(protocol)
    assert ("symptoms", "escalate", "yes") in edges
    assert ("symptoms", "do_action", "no") in edges
    assert ("do_action", "contact_crew", "I can't") in edges
    assert ("check", "deescalate", "Otherwise") in edges
    assert any(source == "check" and '"above": 20' in label for source, _, label in edges)
    graph = protocol_dot(protocol, None)
    assert graph.count(" -> ") == len(edges)
    assert "CURRENT |" not in graph and "VISITED |" not in graph
    for node_id in protocol["nodes"]:
        assert f'"{node_id}" [label=' in graph
    assert protocol == before


def test_visualizer_does_not_imply_pending_episode_is_running():
    from scripts.preview_protocol import fixture_protocol, new_state, protocol_dot

    state = new_state("Pending confirmation", "iss", "moderate")
    graph = protocol_dot(fixture_protocol(), state["episode"])
    assert "CURRENT |" not in graph
    assert "VISITED |" not in graph


def test_visualizer_marks_final_node_after_completion():
    app = preview()
    select(app, "Scenario").set_value("Immediate handover")
    button(app, "Load / restart scenario").click().run()
    button(app, "Continue").click().run()
    assert not app.exception
    graph = app.get("graphviz_chart")[-1].proto.spec
    assert "FINAL | handed_over" in graph
    assert "CURRENT |" not in graph


def test_starting_severity_offers_the_previewed_problem_states(monkeypatch):
    from scripts import preview_protocol as sandbox
    protocol = sandbox.fixture_protocol()
    assert sandbox.severity_options(protocol) == ["mild", "moderate", "severe"]
    assert select(preview(), "Starting severity").options == ["mild", "moderate", "severe"]
    protocol["nodes"]["escalate"]["severity"] = "medical_urgency"
    protocol["nodes"]["route"]["branches"][0]["if"] = {"severity_is": "medical_urgency"}
    monkeypatch.setattr(config, "load_problems", lambda include_examples=False: {"_example": {"symptoms": {}}})
    assert sandbox.severity_options(protocol) == ["watch", "medical_urgency"]
