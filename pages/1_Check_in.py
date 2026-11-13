# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Check-in: measurement form, trigger alert and confirmation step. Owner: Rol 5."""
import streamlit as st

st.title("Check-in")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

st.info("Not built yet (Rol 5). See AGENTS.md: core.episodes.on_new_measurement() and confirm().")
