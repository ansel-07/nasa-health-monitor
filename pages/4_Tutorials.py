# AI-assisted: generated with Claude Code and reviewed by Javi.
"""Tutorials: one practice tutorial per protocol, each with its bar. Owner: Javi.

docs/ASTRONAUT_HEALTH_APP_SPEC.md screen 5 and AGENTS.md 5.6 / 16.4: a tutorial runs the real
protocol with the same engine and flowchart on an in-memory episode ("practice": true), so
nothing is saved (no measurement, detection or episode). It can start only when
activity.can_repeat_tutorial(); reaching the end node refills its bar (activity.complete).
The bar never blocks a real protocol.
No mascot and no voice on this screen (docs/FRONTEND_MASCOT_LAYOUT.md 6).
"""
import streamlit as st

from core import activity, config, protocol_engine
from core.models import OUTCOMES

RUN = "tutorial_run"   # the in-memory practice episode while a tutorial is open


@st.dialog("Whole protocol", width="large")
def show_whole_protocol(episode: dict) -> None:
    """The whole diagram in a large dialog (#233): the focused chart stays as it is."""
    st.graphviz_chart(protocol_engine.flowchart_dot(episode, whole=True), width="stretch",
                      alt="Whole protocol flowchart. The current step is highlighted; completed steps are green.")


def readable(name: str) -> str:
    return str(name).replace("_", " ").capitalize()


def available(astronaut: str, problem_id: str, environment: str) -> bool:
    """True if the protocol can be shown (no TODO content, valid nodes)."""
    try:
        protocol_engine.current_step(protocol_engine.submit(
            protocol_engine.practice_episode(astronaut, problem_id, environment), None))
    except (ValueError, KeyError, OSError):
        return False
    return True


def show_list(astronaut: str, environment: str) -> None:
    problems = config.load_problems()
    st.write("Practise each protocol here, so you know it before you need it. Nothing you enter is saved.")
    if not problems:
        st.info("No protocols are configured yet.")
    for index, (problem_id, problem) in enumerate(problems.items()):
        level = activity.bar_level(astronaut, "tutorial", problem_id)
        if index % 3 == 0:
            grid = st.columns(3)   # rows of three: narrow screens keep the configured order
        with grid[index % 3]:
            with st.container(border=True):
                st.markdown(f":material/school: **{problem['name']}**")
                st.progress(level / 100, text=f"Review recency: {level}%" if level else "Review recency: 0% (due)")
                ready = available(astronaut, problem_id, environment)
                allowed = activity.can_repeat_tutorial(astronaut, problem_id)
                if st.button("Start tutorial", key=f"tutorial_{problem_id}", disabled=not (ready and allowed),
                             use_container_width=True):
                    episode = protocol_engine.practice_episode(astronaut, problem_id, environment)
                    st.session_state[RUN] = protocol_engine.submit(episode, None)
                    st.rerun()
                if not ready:
                    st.caption("This tutorial is not available yet: its protocol is incomplete.")
                elif not allowed:
                    st.caption("Recently practised. You can repeat it when the bar drops below 80%.")


def advance(astronaut: str, episode: dict, response: dict) -> None:
    try:
        updated = protocol_engine.submit(episode, response)
    except (ValueError, KeyError, OSError):
        st.error("Check your response and try again.")
        return
    if updated["status"] in OUTCOMES:
        activity.complete(astronaut, "tutorial", updated["problem"])
    st.session_state[RUN] = updated
    st.rerun()


def close_button(label: str) -> None:
    if st.button(label, use_container_width=True, key="tutorial_close"):
        st.session_state.pop(RUN, None)
        st.rerun()


def show_practice(astronaut: str, episode: dict) -> None:
    try:
        step = protocol_engine.current_step(episode)
    except (ValueError, KeyError, OSError):
        st.error("This tutorial cannot continue: its protocol is incomplete.")
        close_button("Back to Tutorials")
        return
    name = config.load_problems().get(episode["problem"], {}).get("name", "Protocol")
    st.caption(f"Practice: {name} · Nothing you enter is saved.")

    if episode["status"] in OUTCOMES:
        st.success(step["text"])
        st.success("Tutorial completed. Its review bar is full again.")
        close_button("Back to Tutorials")
        return

    with st.container(key="tutorial_step"):
        st.html("<style>.st-key-tutorial_step p { font-size: 1.3rem; line-height: 1.45; }</style>")
        st.markdown(step["text"])
    if st.button("Show whole protocol", icon=":material/open_in_full:", type="tertiary", key="tutorial_whole"):
        show_whole_protocol(episode)
    st.graphviz_chart(protocol_engine.flowchart_dot(episode), width="stretch",
                      alt="Protocol flowchart. The current step is highlighted; completed steps are green.")
    key = f"tutorial_{episode['problem']}_{step['id']}_{len(episode.get('log', []))}"
    kind = step["type"]
    if kind in ("info", "contact"):
        if kind == "contact":
            targets = {"crew_medical_officer": "Crew medical officer", "flight_surgeon": "Flight surgeon"}
            st.write(f"Contact: {targets[step['target']]} (practice: no message is sent)")
        if st.button("Continue", key=f"{key}_continue", use_container_width=True):
            advance(astronaut, episode, {"action": "continue"})
    elif kind == "action":
        # "I can't" only when the protocol has a route for it; never a dead button.
        can_refuse = "next_if_cannot" in step
        done_col, cannot_col = st.columns(2) if can_refuse else (st.container(), None)
        if done_col.button("Done", key=f"{key}_done", use_container_width=True):
            advance(astronaut, episode, {"action": "done"})
        if can_refuse and cannot_col.button("I can't", key=f"{key}_cannot", use_container_width=True):
            advance(astronaut, episode, {"action": "cannot"})
    elif kind == "measure":
        with st.form(f"{key}_measure"):
            value = st.number_input(f"Practice value ({step['unit']})", value=None, key=f"{key}_value")
            submitted = st.form_submit_button("Continue")
        if submitted:
            if value is None:
                st.error("Enter a value before continuing.")
            else:
                advance(astronaut, episode, {"value": value})
    elif kind == "question":
        # One click per answer: each option is its own button.
        options = list(step["options"])
        for column, answer in zip(st.columns(len(options)), options):
            if column.button(readable(answer), key=f"{key}_answer_{answer}", use_container_width=True):
                advance(astronaut, episode, {"answer": answer})
    close_button("Leave tutorial")


if "astronaut" not in st.session_state or "environment" not in st.session_state:
    st.switch_page("pages/0_Home.py")
astronaut = st.session_state["astronaut"]
environment = st.session_state["environment"]

run = st.session_state.get(RUN)
if run and (run["astronaut"] != astronaut or run["environment"] != environment):
    # Astronaut or environment changed on the Welcome screen: the practice run used the old
    # environment, so its branches (e.g. Mars vs Moon) would no longer match. Start again.
    st.session_state.pop(RUN, None)
    run = None
if run:
    show_practice(astronaut, run)
else:
    show_list(astronaut, environment)
