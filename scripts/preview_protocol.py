# AI-assisted: generated with Codex; human review pending.
"""Manual Protocol sandbox. Run: python -m streamlit run scripts/preview_protocol.py.

Uses the existing nonmedical example fixture. Dependency replacements are scoped
and restored after every render; runtime CSV/JSON and medical config are untouched.
This is a separate developer app, never an astronaut-facing source of health data.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import json
import runpy
import sys
from unittest.mock import patch

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import config, data, episodes, mission, protocol_engine
from core.models import severity_rank


SCENARIOS = ["Full journey", "Measurement branches", "Immediate handover", "Pending confirmation", "No episode"]
PROBLEMS = {
    "sandbox_journey": {"name": "Synthetic interface journey (test only)"},
    "sandbox_measure": {"name": "Synthetic measurement routing (test only)"},
}


def fixture_protocol() -> dict:
    """Reuse example thresholds and wait; replace narrative with explicit test text."""
    protocol = config.load_protocol("_example")
    text = {
        "intro": "Synthetic interface test. Press Continue to test a question.",
        "intro_mars": "Synthetic Mars branch. Press Continue to test a question.",
        "symptoms": "Do you have symptoms?: yes exercises escalation; no exercises a timed action.",
        "do_action": "Test action: advance the sandbox clock to enable Done, or select I can't.",
        "remeasure": "Enter a synthetic example value. This is not a health measurement.",
        "contact_crew": "Simulated crew contact. No notification is sent.",
        "contact_now": "Simulated Earth contact. No notification is sent.",
        "monitor": "Synthetic test finished: monitoring branch.",
        "handed_over": "Synthetic test finished: handover branch.",
        "done": "Synthetic test finished: resolved branch.",
    }
    for node_id, value in text.items():
        protocol["nodes"][node_id]["text"] = value
    return protocol


def fixture_check(cond: dict, ctx: dict) -> bool:
    """Test double limited to the existing example's three condition forms.

    It does not implement or replace Juan Carlos's production evaluator.
    """
    if "severity_at_least" in cond:
        return severity_rank(ctx["severity"]) >= severity_rank(cond["severity_at_least"])
    if "environment_in" in cond:
        return ctx["environment"] in cond["environment_in"]
    if "var" in cond and "above" in cond:
        return ctx["vars"][cond["var"]] > cond["above"]
    raise ValueError("Unsupported sandbox condition.")


def new_state(scenario: str, environment: str, severity: str) -> dict:
    clock = datetime.fromisoformat(config.load_mission()["start"])
    episode = None
    if scenario != "No episode":
        problem = "sandbox_measure" if scenario == "Measurement branches" else "sandbox_journey"
        episode = {
            "id": "sandbox-episode", "astronaut": "sandbox-astronaut", "problem": problem,
            "environment": environment, "severity_initial": severity, "severity": severity,
            "status": "pending_confirmation" if scenario == "Pending confirmation" else "active",
            "current_node": {"Measurement branches": "remeasure", "Immediate handover": "contact_now"}.get(scenario),
            "vars": {}, "answers": {}, "log": [], "opened_at": clock.isoformat(),
            "closed_at": None, "outcome": None,
        }
    return {"clock": clock, "episode": episode, "measurements": []}


def protocol_edges(protocol: dict) -> list[tuple[str, str, str]]:
    """Derive labeled edges from the exact runtime definition, in branch order."""
    edges = []
    for node_id, node in protocol["nodes"].items():
        if "next" in node:
            label = "Done" if node["type"] == "action" else "Continue"
            if node["type"] in ("measure", "set_severity"):
                label = ""
            edges.append((node_id, node["next"], label))
        if "next_if_cannot" in node:
            edges.append((node_id, node["next_if_cannot"], "I can't"))
        for answer, target in node.get("options", {}).items():
            edges.append((node_id, target, answer))
        for index, branch in enumerate(node.get("branches", []), 1):
            edges.append((node_id, branch["next"], f"{index}: {json.dumps(branch['if'], sort_keys=True)}"))
        if "default" in node:
            edges.append((node_id, node["default"], "Otherwise"))
    return edges


def protocol_dot(protocol: dict, episode: dict | None) -> str:
    """Build Graphviz source without a Graphviz Python dependency."""
    running = episode is not None and episode["status"] != "pending_confirmation"
    current = (episode.get("current_node") or protocol["start"]) if running else None
    trace = [entry["node"] for entry in episode.get("log", [])] if running else []
    if current:
        trace.append(current)
    taken = set(zip(trace, trace[1:]))
    visited = set(trace)
    quote = json.dumps
    lines = [
        'digraph protocol {',
        'graph [rankdir=TB, bgcolor="transparent", pad="0.15"];',
        'node [shape=box, style="rounded,filled", fillcolor="#f1f5f9", color="#64748b", fontcolor="#0f172a", fontname="Arial", fontsize=22];',
        'edge [color="#94a3b8", fontcolor="#334155", fontname="Arial", fontsize=18];',
    ]
    for node_id, node in protocol["nodes"].items():
        marker = ""
        fill, border = "#f1f5f9", "#64748b"
        if node_id in visited:
            marker, fill, border = "VISITED | ", "#dcfce7", "#15803d"
        if node_id == current:
            marker = "CURRENT | " if episode["status"] == "active" else "FINAL | "
            fill, border = "#fef3c7", "#b45309"
        label = f"{marker}{node_id}\n{node['type']}"
        for field in ("wait_min", "save_as", "severity", "target", "outcome"):
            if field in node:
                label += f"\n{field}: {node[field]}"
        shape = "diamond" if node["type"] == "decision" else "box"
        lines.append(f'{quote(node_id)} [label={quote(label)}, shape={shape}, fillcolor="{fill}", color="{border}"];')
    for source, target, label in protocol_edges(protocol):
        taken_edge = (source, target) in taken
        color = "#15803d" if taken_edge else "#94a3b8"
        width = 3 if taken_edge else 1
        lines.append(f'{quote(source)} -> {quote(target)} [label={quote(label)}, color="{color}", penwidth={width}];')
    lines.append("}")
    return "\n".join(lines)


def show_visualizer(protocol: dict, state: dict) -> None:
    st.subheader("Protocol execution map")
    episode = state["episode"]
    if not episode:
        st.caption("No episode loaded. The map shows the available fixture; nothing is running.")
    elif episode["status"] == "pending_confirmation":
        st.caption("Awaiting confirmation. No protocol node is running.")
    else:
        st.caption(f"Problem: {episode['problem']} · Status: {episode['status']} · Node: {episode.get('current_node') or protocol['start']}")
    st.caption("Amber = current/final node. Green = visited nodes and traversed connections. Gray = not visited. Decisions use the first matching branch, then Otherwise.")
    st.graphviz_chart(protocol_dot(protocol, episode), width="stretch", height="content",
                      alt="Protocol flowchart with node types, conditions, current step and execution history.")
    node_ids = list(protocol["nodes"])
    current = episode.get("current_node") if episode else None
    selected = st.selectbox("Inspect node", node_ids, index=node_ids.index(current or protocol["start"]))
    st.json({"id": selected, **protocol["nodes"][selected]})
    with st.expander("Exact runtime protocol and context"):
        st.caption("This is the example fixture with sandbox text. Conditions and data APIs are test doubles; the engine and Protocol page are the real implementations.")
        st.json({"protocol": protocol, "episode": episode, "mission_time": state["clock"].isoformat()})


def main() -> None:
    st.set_page_config(page_title="Protocol test sandbox", layout="wide")
    st.warning("DEVELOPER SANDBOX — synthetic test data only. Changes stay in this browser session.")
    protocol = fixture_protocol()
    wait = protocol["nodes"]["do_action"]["wait_min"]
    with st.sidebar:
        st.title("Protocol test controls")
        scenario = st.selectbox("Scenario", SCENARIOS)
        environment = st.selectbox("Starting environment", ["iss", "moon", "mars"])
        severity = st.selectbox("Starting severity", ["mild", "moderate", "severe"], index=1)
        if st.button("Load / restart scenario") or "protocol_sandbox" not in st.session_state:
            for key in list(st.session_state):
                if key.startswith("protocol_sandbox-astronaut_"):
                    del st.session_state[key]
            st.session_state["protocol_sandbox"] = new_state(scenario, environment, severity)
        state = st.session_state["protocol_sandbox"]
        if st.button(f"Advance {wait:g} minute(s)"):
            state["clock"] += timedelta(minutes=wait)
        delay = st.number_input("Synthetic one-way delay (minutes)", min_value=0.0, value=float(wait))
        missing_delay = st.checkbox("Test missing contact delay")
        pending = st.checkbox("Show a synthetic pending issue after closure")
        st.caption(f"Sandbox mission time: {state['clock'].isoformat()}")
        st.caption("Scenario settings apply when you press Load / restart scenario.")
        st.markdown("**Measurement routes from the existing fixture:** ≤10 resolves; >10 to 20 monitors; >20 escalates to handover.")

    st.session_state["astronaut"] = "sandbox-astronaut"
    st.session_state["environment"] = state["episode"]["environment"] if state["episode"] else environment

    def load_episodes(astronaut=None):
        episode = state["episode"]
        return [deepcopy(episode)] if episode and (astronaut is None or episode["astronaut"] == astronaut) else []

    def get_open_episode(astronaut):
        return next((item for item in load_episodes(astronaut) if item["status"] in ("active", "pending_confirmation")), None)

    def save_episode(episode):
        state["episode"] = deepcopy(episode)

    def latest_values(astronaut):
        return {item["indicator"]: item["value"] for item in state["measurements"] if item["astronaut"] == astronaut}

    def page_link(page, *, label, **kwargs):
        # Navigation to production pages would leave the isolated sandbox.
        st.caption(f"{label}: navigation is disabled in this test app. Use the scenario controls instead.")

    replacements = [
        (config, "load_problems", lambda include_examples=False: deepcopy(PROBLEMS)),
        (protocol_engine, "load_protocol", lambda problem_id: deepcopy(protocol)),
        (protocol_engine, "load_environments", lambda: {
            env: {"comm_delay_min": "TODO_EDU" if missing_delay else delay} for env in ("iss", "moon", "mars")}),
        (protocol_engine.conditions, "check", fixture_check),
        (mission, "now", lambda: state["clock"]),
        (data, "load_episodes", load_episodes),
        (data, "get_open_episode", get_open_episode),
        (data, "save_episode", save_episode),
        (data, "latest_values", latest_values),
        (data, "add_measurement", lambda measurement: state["measurements"].append(deepcopy(measurement))),
        (episodes, "get_pending", lambda astronaut: [
            {"astronaut": astronaut, "problem": "sandbox_measure", "severity": "severe"}] if pending else []),
        (st, "page_link", page_link),
    ]
    with ExitStack() as stack:
        for module, name, replacement in replacements:
            stack.enter_context(patch.object(module, name, replacement))
        runpy.run_path(str(ROOT / "pages" / "2_Protocol.py"), run_name="__main__")
    # Use the full page width and natural height instead of shrinking the entire
    # graph into a narrow column and a fixed-height viewport.
    show_visualizer(protocol, state)
    with st.expander("Inspect saved test episode and measurements"):
        st.json({"episode": state["episode"], "measurements": state["measurements"]})


if __name__ == "__main__":
    main()
