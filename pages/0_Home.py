# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Home ("login"): pick astronaut and environment, mascot greeting, go to the other screens. Owner: Ansel.

Run through app.py (st.navigation), which sets the page config. Provisional layout until the
team's UI document: the mascot large and centered with its subtitles, the selectors below it,
then the buttons that lead to the other screens (there is no sidebar menu).
"""
import streamlit as st

from core import config, data, episodes, mascot

astronauts = data.load_astronauts()
environments = config.load_environments()
mission = config.load_mission()

ids = list(astronauts["id"])
names = dict(zip(astronauts["id"], astronauts["name"]))
env_ids = list(environments)

# Session keys are plain (non-widget) keys so they survive page changes.
if "astronaut" not in st.session_state:
    st.session_state["astronaut"] = ids[0]
if "environment" not in st.session_state:
    st.session_state["environment"] = mission["environment"]

title_col, voice_col = st.columns([5, 1], vertical_alignment="bottom")
with title_col:
    st.title("TODO: project name")
    st.caption("Prototype, not a medical device. It guides; it does not diagnose.")
with voice_col:
    mascot.voice_toggle()

astronaut = st.session_state["astronaut"]
open_episode = data.get_open_episode(astronaut)
pending = episodes.get_pending(astronaut)

# Placeholder lines: final wording and moods are still to be decided by the team.
if open_episode:
    greeting, mood = f"Hi {names[astronaut]}. We have an open issue to take care of.", "worried"
elif pending:
    greeting, mood = f"Hi {names[astronaut]}. I have {len(pending)} alert(s) waiting for you.", "thinking"
else:
    greeting, mood = f"Hi {names[astronaut]}! Everything looks fine. Ready for your check-in?", "happy"

_, center, _ = st.columns([1, 2, 1])
with center:
    mascot.say(greeting, mood, size="large")

    pick_astronaut, pick_environment = st.columns(2)
    with pick_astronaut:
        st.session_state["astronaut"] = st.selectbox(
            "Who are you?", ids, index=ids.index(st.session_state["astronaut"]),
            format_func=lambda i: names[i],
        )
    with pick_environment:
        st.session_state["environment"] = st.selectbox(
            "Where is the mission?", env_ids, index=env_ids.index(st.session_state["environment"]),
            format_func=lambda e: environments[e]["name"],
        )

    buttons = st.columns(4 if open_episode and open_episode["status"] == "active" else 3)
    if buttons[0].button("Start check-in", type="primary", use_container_width=True):
        st.switch_page("pages/1_Check_in.py")
    if open_episode and open_episode["status"] == "active":
        if buttons[1].button("Continue protocol", use_container_width=True):
            st.switch_page("pages/2_Protocol.py")
    if buttons[-2].button("View history", use_container_width=True):
        st.switch_page("pages/3_Trends.py")
    if buttons[-1].button("Reset demo", use_container_width=True):
        data.reset_demo()
        st.rerun()
