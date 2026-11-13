# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Home page: pick astronaut and environment, see open episode, reset the demo. Owner: Rol 3."""
import streamlit as st

from core import config, data, episodes

st.set_page_config(page_title="Astronaut Health Monitor", page_icon="🩺", layout="wide")

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

col1, col2 = st.columns(2)
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

astronaut = st.session_state["astronaut"]
open_episode = data.get_open_episode(astronaut)
pending = episodes.get_pending(astronaut)

if open_episode:
    st.warning(f"Open problem: {open_episode['problem']} ({open_episode['severity']}). Go to Protocol.")
elif pending:
    st.info(f"{len(pending)} pending alert(s).")
else:
    st.success("No open problems.")

st.divider()
if st.button("Reset demo"):
    data.reset_demo()
    st.rerun()
