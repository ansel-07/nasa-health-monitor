# AI-assisted: generated with Codex; human review by Edu pending.
"""Execute the #137 medical-content branches with the real protocol engine."""
from copy import deepcopy
from pathlib import Path
import re

import pytest

from core import config, data, models, protocol_engine, triggers


@pytest.fixture
def run_context(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(data, "latest_values", lambda astronaut: {})

    def start(pid, environment, concern=False, severity="watch"):
        symptoms = {name: "not_present" for name in config.load_problems()[pid]["symptoms"]}
        first = next(iter(symptoms))
        symptoms[first] = "concern" if concern else "watch"
        monkeypatch.setattr(triggers, "symptom_levels", lambda *args: dict(symptoms))
        episode = protocol_engine.practice_episode("a1", pid, environment)
        episode.pop("practice")  # Exercise actual persistence, not tutorial-only behavior.
        episode.update(id="ep-content", severity=severity)
        return protocol_engine.submit(episode, None)

    return start


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
@pytest.mark.parametrize("concern", [False, True])
@pytest.mark.parametrize("limits_task", ["yes", "no"])
def test_watch_has_one_local_contact_and_at_most_five_visible_steps(
        run_context, pid, environment, concern, limits_task):
    episode = run_context(pid, environment, concern)
    seen, contacts = [], []
    for _ in range(10):
        step = protocol_engine.current_step(episode)
        seen.append(step)
        if step["type"] == "end":
            break
        if step["type"] == "contact":
            contacts.append(step)
        response = ({"answer": limits_task if step["save_as"] == "limits_task" else "no"}
                    if step["type"] == "question" else
                    {"action": "done" if step["type"] == "action" else "continue"})
        episode = protocol_engine.submit(episode, response)
    assert episode["status"] == "monitoring" and episode["severity"] == "watch"
    assert len(seen) <= 5
    assert [step["target"] for step in contacts] == ["crew_medical_officer"]
    priority = concern or (pid == "muscle_atrophy" and limits_task == "yes")
    assert (contacts[0]["id"] == "w_priority_review") == priority
    assert data.load_episodes()[0]["status"] == "monitoring"


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
@pytest.mark.parametrize("earth_support", ["yes", "no"])
@pytest.mark.parametrize("cannot_stop", [False, True])
@pytest.mark.parametrize("initial_severity", ["watch", "medical_urgency"])
def test_urgency_contacts_local_first_and_cannot_close_before_review(
        run_context, pid, environment, earth_support, cannot_stop, initial_severity):
    episode = run_context(pid, environment, severity=initial_severity)
    contacts = []
    for _ in range(12):
        step = protocol_engine.current_step(episode)
        if step["id"] == "u_handover":
            break
        assert step["type"] != "measure"  # No remeasurement gate before medical help.
        if step["type"] == "contact":
            contacts.append(step["target"])
        if step["type"] == "question":
            response = {"answer": "yes" if step["save_as"] == "red_flags" else earth_support}
        elif step["type"] == "action":
            response = {"action": "cannot" if cannot_stop and step["id"] == "u_stop" else "done"}
        else:
            response = {"action": "continue"}
        episode = protocol_engine.submit(episode, response)
    assert episode["current_node"] == "u_handover"
    assert contacts == (["crew_medical_officer", "flight_surgeon"] if earth_support == "yes"
                        else ["crew_medical_officer"])
    for _ in range(2):
        episode = protocol_engine.submit(episode, {"action": "cannot"})
        assert episode["current_node"] == "u_handover"
        assert episode["status"] == "active" and episode["severity"] == "medical_urgency"
        # Reload/refresh cannot silently finish or downgrade the handover task.
        episode = protocol_engine.submit(deepcopy(data.load_episodes()[0]), None)
        assert episode["status"] == "active" and episode["current_node"] == "u_handover"
    episode = protocol_engine.submit(episode, {"action": "done"})
    assert episode["status"] == episode["outcome"] == "handed_over"
    assert episode["severity"] == "medical_urgency"  # Not resolved or normalized by handover.


@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_missing_eye_results_are_referred_instead_of_assumed_normal(run_context, environment):
    episode = run_context("sans", environment)
    episode = protocol_engine.submit(episode, {"answer": "no"})  # Red flags absent.
    episode = protocol_engine.submit(episode, {"action": "continue"})  # Routine local contact.
    assert episode["current_node"] == "w_acuity"
    episode = protocol_engine.submit(episode, {"action": "cannot"})
    step = protocol_engine.current_step(episode)
    assert step["id"] == "w_missing_data" and step["target"] == "crew_medical_officer"
    assert "unavailable or invalid" in step["text"]
    assert episode["status"] == "active"  # Missing data is not an automatic closure.


def test_muscle_red_flags_include_general_emergencies():
    text = config.load_protocol("muscle_atrophy")["nodes"]["w_red_flags"]["text"].lower()
    assert "breathing difficulty" in text and "loss of consciousness" in text
    assert "general emergency" in text


@pytest.mark.parametrize("pid,diagram_index", [("sans", 0), ("muscle_atrophy", 1)])
def test_regenerated_diagrams_match_executable_nodes_and_edges(pid, diagram_index):
    document = (Path(__file__).resolve().parents[1] / "docs" / "PROTOCOL_FLOWCHARTS.md").read_text(encoding="utf-8")
    diagram = document.split("```mermaid\n")[diagram_index + 1].split("```", 1)[0]
    protocol = config.load_protocol(pid)
    nodes = protocol["nodes"]
    assert set(re.findall(r'^    (\w+)[\[{]', diagram, re.M)) == set(nodes)
    drawn_edges = set(re.findall(r'^    (\w+) -->\|[^\n]*?\| (\w+)$', diagram, re.M))
    expected_edges = {(nid, target) for nid, node in nodes.items()
                      for target in config._node_targets(node)}
    assert drawn_edges == expected_edges
    # Every route is acyclic except the explicit, user-driven pending-handover task.
    def visit(nid, ancestors):
        assert nid not in ancestors, f"Unexpected cycle through {nid}"
        for target in config._node_targets(nodes[nid]):
            if target == nid == "u_handover":
                continue
            visit(target, ancestors | {nid})
    visit(protocol["start"], set())


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
def test_iss_no_red_flags_page_displays_the_configured_narration(run_context, monkeypatch, pid):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from core import episodes, mascot

    run_context(pid, "iss")
    monkeypatch.setattr(data, "get_open_episode", lambda _: data.load_episodes()[0])
    monkeypatch.setattr(episodes, "get_pending", lambda _: [])
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: st.info(text))
    app = AppTest.from_file("../pages/2_Protocol.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "iss"
    app.run()
    assert not app.exception
    expected = config.load_protocol(pid)["nodes"]["w_red_flags"]["text"]
    assert any(item.value == expected for item in app.info)
    next(button for button in app.button if button.label == "No").click().run()
    assert not app.exception
    current = data.load_episodes()[0]["current_node"]
    assert current == ("w_notify" if pid == "sans" else "w_limits")
    assert any(item.value == config.load_protocol(pid)["nodes"][current]["text"]
               for item in app.info)
