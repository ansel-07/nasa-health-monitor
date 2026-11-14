# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Home ("login"): pick astronaut and environment, mascot greeting, reset the demo. Owner: Ansel.

Run through app.py (st.navigation), which also sets the page config.
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

st.title("TODO: project name")
st.caption("Prototype, not a medical device. It guides; it does not diagnose.")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.session_state["astronaut"] = st.selectbox(
        "Who are you?",
        ids,
        index=ids.index(st.session_state["astronaut"]),
        format_func=lambda i: names[i],
    )
with col2:
    st.session_state["environment"] = st.selectbox(
        "Where is the mission?",
        env_ids,
        index=env_ids.index(st.session_state["environment"]),
        format_func=lambda e: environments[e]["name"],
    )
with col3:
    mascot.voice_toggle()

astronaut = st.session_state["astronaut"]
open_episode = data.get_open_episode(astronaut)
pending = episodes.get_pending(astronaut)

# Placeholder lines: final wording and moods are still to be decided by the team.
if open_episode:
    mascot.say(f"Hi {names[astronaut]}. We have an open issue to take care of. Let's go to Protocol.", "worried")
elif pending:
    mascot.say(f"Hi {names[astronaut]}. I have {len(pending)} alert(s) waiting for you.", "thinking")
else:
    mascot.say(f"Hi {names[astronaut]}! Everything looks fine. Ready for your check-in?", "happy")

st.divider()
if st.button("Reset demo"):
    data.reset_demo()
    st.rerun()
