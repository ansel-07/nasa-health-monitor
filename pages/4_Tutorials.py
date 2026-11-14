# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Tutorials: one practice tutorial per protocol, each with its bar. Owner: Javi.

STUB (Javi): docs/ASTRONAUT_HEALTH_APP_SPEC.md screen 5 and AGENTS.md 5.6 / 16. Replace with the
practice run of each protocol (same engine and flowchart, episode with "practice": true, nothing
saved), enabled only when activity.can_repeat_tutorial(); on completion activity.complete().
"""
import streamlit as st

from core import activity, config, mascot

if "astronaut" not in st.session_state:
    st.switch_page("pages/0_Home.py")
astronaut = st.session_state["astronaut"]

st.title("Tutorials")
with mascot.beside("Practise each protocol here, so you know it before you need it.", "neutral"):
    problems = config.load_problems()
    if not problems:
        st.info("No protocols are configured yet.")
    for problem_id, problem in problems.items():
        level = activity.bar_level(astronaut, "tutorial", problem_id)
        st.markdown(f"**{problem['name']}**")
        st.progress(level / 100, text=f"{level}%" if level else "Not completed yet")
        st.button("Start tutorial (coming soon)", key=f"tutorial_{problem_id}", disabled=True)
