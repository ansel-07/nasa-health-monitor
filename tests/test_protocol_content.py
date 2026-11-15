# AI-assisted: generated with Codex and Claude Code, reviewed by Edu and Javi.
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
def test_watch_stays_in_monitoring_after_completed_review(
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
    assert len(seen) <= 6  # Expanded review paths await Gonzalo rehearsal approval.
    assert [step["target"] for step in contacts] == ["crew_medical_officer"]
    priority = concern or (pid == "muscle_atrophy" and limits_task == "yes")
    assert (contacts[0]["id"] == "w_priority_review") == priority
    assert data.load_episodes()[0]["status"] == "monitoring"


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
@pytest.mark.parametrize("earth_support", ["yes", "no"])
@pytest.mark.parametrize("initial_severity", ["watch", "medical_urgency"])
def test_urgency_contacts_local_first_and_cannot_close_before_review(
        run_context, pid, environment, earth_support, initial_severity):
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
            assert step["id"] != "u_stop" or "next_if_cannot" not in step   # one exit: no duplicate contact
            response = {"action": "done"}
        else:
            response = {"action": "continue"}
        episode = protocol_engine.submit(episode, response)
    assert episode["current_node"] == "u_handover"
    expected = ["crew_medical_officer"]
    if environment != "moon" or earth_support == "yes":
        expected.append("flight_surgeon")
    assert contacts == expected
    for _ in range(2):
        episode = protocol_engine.submit(episode, {"action": "cannot"})
        assert episode["current_node"] == "u_no_clinician"
        assert episode["status"] == "active" and episode["severity"] == "medical_urgency"
        # Refresh preserves guidance and cannot accept handover or downgrade urgency.
        episode = protocol_engine.submit(deepcopy(data.load_episodes()[0]), None)
        assert episode["status"] == "active" and episode["current_node"] == "u_no_clinician"
        assert protocol_engine.current_step(episode)["type"] == "info"
        episode = protocol_engine.submit(episode, {"action": "continue"})
        assert episode["current_node"] == "u_handover"
        assert episode["status"] == "active" and episode["severity"] == "medical_urgency"
        assert episode["closed_at"] is None and episode["outcome"] is None
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
            if nid == "u_no_clinician" and target == "u_handover":
                # Only the user-driven guidance acknowledgement returns to the hold.
                assert nodes[nid]["type"] == "info"
                assert nodes["u_handover"]["next_if_cannot"] == nid
                continue
            visit(target, ancestors | {nid})
    visit(protocol["start"], set())


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_clinician_can_escalate_priority_review(run_context, pid, environment):
    episode = run_context(pid, environment, concern=True)
    episode = protocol_engine.submit(episode, {"answer": "no"})
    assert episode["current_node"] == "w_priority_review"
    episode = protocol_engine.submit(episode, {"action": "continue"})
    assert episode["current_node"] == "w_review_outcome"
    assert episode["status"] == "active" and episode["severity"] == "watch"
    episode = protocol_engine.submit(episode, None)
    assert episode["current_node"] == "w_review_outcome"
    episode = protocol_engine.submit(episode, {"answer": "yes"})
    assert episode["current_node"] == "u_stop"
    assert episode["severity"] == "medical_urgency"


@pytest.mark.parametrize("insufficient", ["yes", "no"])
def test_sans_correction_escalation_uses_explicit_clinician_answer(run_context, insufficient):
    episode = run_context("sans", "iss")
    for response in ({"answer": "no"}, {"action": "continue"}, {"action": "done"}, {"answer": "yes"}):
        episode = protocol_engine.submit(episode, response)
    assert episode["current_node"] == "w_correction_check"
    episode = protocol_engine.submit(episode, {"answer": insufficient})
    assert episode["current_node"] == ("u_stop" if insufficient == "yes" else "w_correction")
    assert episode["severity"] == ("medical_urgency" if insufficient == "yes" else "watch")


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
def test_previous_protocol_node_ids_remain_available(pid):
    nodes = config.load_protocol(pid)["nodes"]
    # u_mars_send was merged into the identical ISS contact (Javi, protocol structure).
    # u_help was removed: it only repeated the crew-medical-officer contact (Javi, protocol structure).
    legacy = {"u_support", "u_handover"}
    legacy |= {"u_orbit", "u_moon"} if pid == "muscle_atrophy" else {"u_ground"}
    assert legacy <= set(nodes)


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


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "moon", "mars"])
def test_unavailable_handover_page_shows_guidance_without_closing(
        run_context, monkeypatch, pid, environment):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from core import episodes, mascot

    episode = run_context(pid, environment, severity="medical_urgency")
    episode["current_node"] = "u_handover"
    data.save_episode(episode)
    monkeypatch.setattr(data, "get_open_episode", lambda _: data.load_episodes()[0])
    monkeypatch.setattr(episodes, "get_pending", lambda _: [])
    monkeypatch.setattr(mascot, "say", lambda text, *args, **kwargs: st.info(text))
    app = AppTest.from_file("../pages/2_Protocol.py", default_timeout=30)
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = environment
    app.run()
    assert not app.exception
    next(b for b in app.button if b.label == "I can't").click().run()
    assert not app.exception
    expected = config.load_protocol(pid)["nodes"]["u_no_clinician"]["text"]
    assert any(item.value == expected for item in app.info)
    assert data.load_episodes()[0]["current_node"] == "u_no_clinician"
    app.run()
    assert any(item.value == expected for item in app.info)
    next(b for b in app.button if b.label == "Continue").click().run()
    assert not app.exception
    saved = data.load_episodes()[0]
    assert saved["current_node"] == "u_handover"
    assert saved["status"] == "active" and saved["severity"] == "medical_urgency"
    assert saved["closed_at"] is None and saved["outcome"] is None
    next(b for b in app.button if b.label == "Done").click().run()
    assert not app.exception
    assert data.load_episodes()[0]["status"] == "handed_over"


# Structural guards (Javi owns protocol structure, AGENTS.md 4): no branch that only looks like a choice.
def _same_step(nodes, a, b):
    """Two steps the astronaut cannot tell apart: same kind, addressee, text and next steps."""
    keys = ("type", "target", "text", "outcome", "severity")
    return (all(nodes[a].get(k) == nodes[b].get(k) for k in keys)
            and sorted(config._node_targets(nodes[a])) == sorted(config._node_targets(nodes[b])))


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
def test_no_branch_leads_to_identical_steps(pid):
    nodes = config.load_protocol(pid)["nodes"]
    for nid, node in nodes.items():
        targets = sorted(set(config._node_targets(node)) - {nid})
        assert len(targets) == len(set(targets))
        for i, a in enumerate(targets):
            for b in targets[i + 1:]:
                assert not _same_step(nodes, a, b), f"{nid}: '{a}' and '{b}' are the same step"


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
def test_every_i_cant_changes_the_step_and_every_step_can_finish(pid):
    protocol = config.load_protocol(pid)
    nodes = protocol["nodes"]
    for nid, node in nodes.items():
        assert node.get("next_if_cannot") != nid, f"{nid}: 'I can't' returns to the same step"
    ends = {nid for nid, node in nodes.items() if node["type"] == "end"}

    def reach(start):
        seen, todo = set(), [start]
        while todo:
            current = todo.pop()
            if current not in seen:
                seen.add(current)
                todo.extend(config._node_targets(nodes[current]))
        return seen

    for nid in reach(protocol["start"]):
        assert reach(nid) & ends, f"{nid} cannot reach an end"


@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
@pytest.mark.parametrize("environment", ["iss", "mars"])
def test_urgent_iss_and_mars_share_one_flight_surgeon_step(run_context, pid, environment):
    episode = run_context(pid, environment, severity="medical_urgency")
    contacts = []
    for _ in range(10):
        step = protocol_engine.current_step(episode)
        if step["id"] == "u_handover":
            break
        if step["type"] == "contact":
            contacts.append((step["id"], step["target"], "response_delay_min" in step))
        episode = protocol_engine.submit(episode, {"action": "done" if step["type"] == "action" else "continue"})
    expected = "u_orbit" if pid == "muscle_atrophy" else "u_ground"
    assert contacts[-1] == (expected, "flight_surgeon", True)



@pytest.mark.parametrize("pid", ["sans", "muscle_atrophy"])
def test_no_route_contacts_the_same_person_twice_in_a_row(pid):
    """A contact straight after a contact to the same person is a duplicate step (e.g. the old u_help)."""
    nodes = config.load_protocol(pid)["nodes"]
    for nid, node in nodes.items():
        if node["type"] != "contact":
            continue
        for target in config._node_targets(node):
            nxt = nodes[target]
            assert not (nxt["type"] == "contact" and nxt["target"] == node["target"]), \
                f"{nid} -> {target}: two {node['target']} contacts in a row"
