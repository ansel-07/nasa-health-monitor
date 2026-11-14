# AI-assisted: generated with Claude Code and Codex; human review pending.
"""Protocol: run the active episode step by step. Owner: Javi."""
import streamlit as st

from core import config, data, episodes, mascot, protocol_engine
from core.models import OUTCOMES


def show_pending(astronaut: str) -> None:
    """Read Juan Carlos's severity-ordered queue without promoting an episode."""
    # Integration with Juan Carlos: get_pending() is read-only. A contract for
    # promoting its first item to pending_confirmation is still needed.
    problems = config.load_problems()
    pending = [item for item in episodes.get_pending(astronaut) if item["problem"] in problems]
    if pending:
        next_item = pending[0]
        name = problems[next_item["problem"]]["name"]
        if name.startswith("TODO"):
            name = "Pending issue"
        st.info(f"{len(pending)} issue(s) awaiting confirmation. Next: {name} ({next_item['severity']}).")
        st.page_link("pages/1_Check_in.py", label="Go to Check-in")


def advance(episode: dict, response: dict) -> None:
    """Delegate validation, measurements and persistence to the engine."""
    try:
        protocol_engine.submit(episode, response)
    except (ValueError, KeyError, OSError):
        st.error("The step could not be saved or completed. Check your response and try again. If this continues, ask the mission team for help.")
        return
    st.rerun()


def show_result(episode: dict, step: dict, astronaut: str) -> None:
    mascot.say(step["text"], "neutral", size="large")
    labels = {"resolved": "Resolved", "monitoring": "Monitoring", "handed_over": "Handed over"}
    st.success(f"Protocol completed: {labels[episode['status']]}")
    if episode.get("closed_at"):
        st.caption(f"Completed at mission time {episode['closed_at']}")
    show_pending(astronaut)


def main() -> None:
    st.title("Protocol")
    mascot.voice_toggle()
    astronaut = st.session_state.get("astronaut")
    if not astronaut:
        mascot.say("Choose an astronaut on the Home page first.", "neutral", size="large")
        st.page_link("app.py", label="Go to Home")
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

    mascot.say(step["text"], "neutral", size="large")
    st.caption(f"Severity: {episode['severity']} · Environment: {episode['environment']}")
    # Log length distinguishes repeated visits to the same node, clearing old
    # form values when a protocol loops back for another measurement or answer.
    key = f"protocol_{astronaut}_{episode['id']}_{step['id']}_{len(episode.get('log', []))}"
    kind = step["type"]
    if kind in ("info", "contact"):
        if kind == "contact":
            targets = {"crew_medical_officer": "Crew medical officer", "flight_surgeon": "Flight surgeon"}
            st.write(f"Contact: {targets[step['target']]}")
            st.caption(f"Estimated response delay: {step['response_delay_min']:g} minutes.")
        if st.button("Continue", key=f"{key}_continue"):
            advance(episode, {"action": "continue"})
    elif kind == "action":
        remaining = step["remaining_wait_min"]
        if remaining > 0:
            st.info(f"Wait remaining: {remaining:.2f} mission minutes.")
            if st.button("Refresh wait", key=f"{key}_refresh"):
                st.rerun()
        done_col, cannot_col = st.columns(2)
        if done_col.button("Done", disabled=remaining > 0, key=f"{key}_done"):
            advance(episode, {"action": "done"})
        if cannot_col.button("I can't", disabled="next_if_cannot" not in step, key=f"{key}_cannot"):
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
        with st.form(f"{key}_question"):
            answer = st.radio("Choose an answer", list(step["options"]), index=None, key=f"{key}_answer")
            submitted = st.form_submit_button("Submit answer")
        if submitted:
            if answer is None:
                st.error("Choose an answer before continuing.")
            else:
                advance(episode, {"answer": answer})
    else:
        st.error("This protocol step is unavailable. Please ask the mission team for help.")


main()
