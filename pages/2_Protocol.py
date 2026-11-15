# AI-assisted: generated with Claude Code and Codex; human review pending.
"""Protocol: run the active episode step by step. Owner: Javi."""
from datetime import datetime

import streamlit as st

from core import config, data, episodes, mascot, protocol_engine
from core.models import OUTCOMES


def problem_name(problems: dict, problem_id: str) -> str:
    name = problems.get(problem_id, {}).get("name", "")
    return name if isinstance(name, str) and name and not name.startswith("TODO") else "Pending issue"


def show_pending(astronaut: str, active: dict | None = None) -> None:
    """List the active protocol and every pending alert, most severe first (spec screen 6).

    Pending alerts keep their queue (episodes.get_pending order); Check-in starts their
    confirmation (episodes.accept_pending). Status is written in words, not only colour.
    """
    problems = config.load_problems()
    pending = [item for item in episodes.get_pending(astronaut) if item["problem"] in problems]
    if not pending and not active:
        return
    st.divider()
    st.subheader("Your protocols")
    if active:
        st.markdown(f"- **{problem_name(problems, active['problem'])}** · Severity: "
                    f"{readable(active['severity'])} · **In progress** (shown above)")
    if pending:
        next_item = pending[0]
        st.info(f"{len(pending)} issue(s) awaiting confirmation. "
                f"Next: {problem_name(problems, next_item['problem'])} ({readable(next_item['severity'])}).")
        st.markdown("\n".join(
            f"{number}. **{problem_name(problems, item['problem'])}** · Severity: {readable(item['severity'])}"
            " · Waiting for a repeat measurement" for number, item in enumerate(pending, 1)))
        st.caption("Most severe first. One protocol runs at a time; the next one starts with a repeat measurement in Check-in.")
        st.page_link("pages/1_Check_in.py", label="Go to Check-in")


def advance(episode: dict, response: dict) -> None:
    """Delegate validation, measurements and persistence to the engine."""
    try:
        protocol_engine.submit(episode, response)
    except (ValueError, KeyError, OSError):
        st.error("The step could not be saved or completed. Check your response and try again. If this continues, ask the mission team for help.")
        return
    st.rerun()


def readable(name: str) -> str:
    """Internal names as plain words for the astronaut: "medical_urgency" -> "Medical urgency"."""
    return str(name).replace("_", " ").capitalize()


def environment_name(environment: str) -> str:
    """Configured environment name (e.g. "Mars base"), or the readable id if it has none."""
    name = config.load_environments().get(environment, {}).get("name", "")
    return name if isinstance(name, str) and name and not name.startswith("TODO") else readable(environment)


def format_mission_time(timestamp: str) -> str:
    """Mission timestamp as "10 Apr 2027, 08:12"."""
    return datetime.fromisoformat(timestamp).strftime("%d %b %Y, %H:%M")


def format_delay(minutes: float) -> str:
    """Readable response delay: seconds under one minute (e.g. the Moon), minutes above."""
    seconds = round(minutes * 60)
    if seconds < 1:
        return "less than 1 second"
    if seconds < 60:
        return f"about {seconds} second{'s' if seconds != 1 else ''}"
    rounded = round(minutes, 1)
    return f"{rounded:g} minute{'s' if rounded != 1 else ''}"


def show_result(episode: dict, step: dict, astronaut: str) -> None:
    mascot.say(step["text"], "neutral", size="large")
    labels = {"resolved": "Resolved", "monitoring": "Monitoring", "handed_over": "Handed over"}
    st.success(f"Protocol completed: {labels[episode['status']]}")
    if episode.get("closed_at"):
        st.caption(f"Completed at mission time {format_mission_time(episode['closed_at'])}")
    show_pending(astronaut)


def main() -> None:
    mascot.voice_toggle()
    astronaut = st.session_state.get("astronaut")
    if not astronaut:
        mascot.say("Choose an astronaut on the Home page first.", "neutral", size="large")
        st.page_link("pages/0_Home.py", label="Go to Home")
        return

    episode = data.get_open_episode(astronaut)
    if episode and episode["problem"].startswith("_"):
        mascot.say("No astronaut protocol is available for this issue.", "neutral", size="large")
        return
    if episode and episode["status"] == "pending_confirmation":
        mascot.say("This issue needs a repeat measurement before a protocol can start. Go to Check-in to complete confirmation.", "neutral", size="large")
        st.page_link("pages/1_Check_in.py", label="Go to Check-in")
        return

    if not episode:
        # Read the saved outcome rather than retaining a session copy that could
        # survive Reset demo or a switch to another astronaut.
        completed = [item for item in data.load_episodes(astronaut)
                     if item["status"] in OUTCOMES and not item["problem"].startswith("_")]
        if completed:
            episode = max(completed, key=lambda item: item.get("closed_at") or "")
        else:
            mascot.say("You have no active protocol.", "neutral", size="large")
            show_pending(astronaut)
            st.page_link("pages/1_Check_in.py", label="Open Check-in")
            return

    try:
        if episode["status"] == "active":
            # Resolve decisions, severity updates and timed-action entry once
            # through the engine before rendering the next interactive step.
            episode = protocol_engine.submit(episode, None)
        step = protocol_engine.current_step(episode)
    except (ValueError, KeyError, OSError):
        mascot.say("This protocol is unavailable because required information is missing or invalid. Please ask the mission team for help.", "neutral", size="large")
        st.error("The protocol cannot continue until the missing information is available.")
        return

    if episode["status"] in OUTCOMES:
        show_result(episode, step, astronaut)
        return

    # Mascot small on the left, the whole protocol on the right, controls below (AGENTS.md 8).
    with mascot.beside(step["text"], "neutral"):
        # Readable by default (around the current step); the whole protocol on request.
        whole = st.toggle("Show whole protocol", key=f"protocol_whole_{astronaut}")
        st.graphviz_chart(protocol_engine.flowchart_dot(episode, whole=whole), width="stretch",
                          alt="Protocol flowchart. The current step is highlighted; completed steps are green.")
    st.caption(f"Severity: {readable(episode['severity'])} · Environment: {environment_name(episode['environment'])}")
    # Log length distinguishes repeated visits to the same node, clearing old
    # form values when a protocol loops back for another measurement or answer.
    key = f"protocol_{astronaut}_{episode['id']}_{step['id']}_{len(episode.get('log', []))}"
    kind = step["type"]
    if kind in ("info", "contact"):
        if kind == "contact":
            targets = {"crew_medical_officer": "Crew medical officer", "flight_surgeon": "Flight surgeon"}
            st.write(f"Contact: {targets[step['target']]}")
            if "response_delay_min" in step:   # Earth contact: round-trip signal time only (#141)
                st.caption(f"Signal round trip to Earth: {format_delay(step['response_delay_min'])}. "
                           "A clinical answer can take longer.")
            else:
                st.caption("On board: no Earth signal delay.")
        if st.button("Continue", key=f"{key}_continue"):
            advance(episode, {"action": "continue"})
    elif kind == "action":
        remaining = step["remaining_wait_min"]
        if remaining > 0:
            st.info(f"Wait remaining: {remaining:.2f} mission minutes.")
            if st.button("Refresh wait", key=f"{key}_refresh"):
                st.rerun()
        # "I can't" only when the protocol has a route for it; never a dead button.
        can_refuse = "next_if_cannot" in step
        done_col, cannot_col = st.columns(2) if can_refuse else (st.container(), None)
        if done_col.button("Done", disabled=remaining > 0, key=f"{key}_done", use_container_width=True):
            advance(episode, {"action": "done"})
        if can_refuse and cannot_col.button("I can't", key=f"{key}_cannot", use_container_width=True):
            advance(episode, {"action": "cannot"})
    elif kind == "measure":
        with st.form(f"{key}_measure"):
            value = st.number_input(f"Measurement ({step['unit']})", value=None, key=f"{key}_value")
            submitted = st.form_submit_button("Save measurement")
        if submitted:
            if value is None:
                st.error("Enter a measurement before continuing.")
            else:
                advance(episode, {"value": value})
    elif kind == "question":
        # One click per answer: each option is its own button.
        options = list(step["options"])
        for column, answer in zip(st.columns(len(options)), options):
            if column.button(readable(answer), key=f"{key}_answer_{answer}", use_container_width=True):
                advance(episode, {"answer": answer})
    else:
        st.error("This protocol step is unavailable. Please ask the mission team for help.")

    show_pending(astronaut, active=episode)


main()
