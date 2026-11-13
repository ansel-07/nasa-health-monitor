# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Trends: indicators over time with colour bands and personal baseline. Owner: Rol 4."""
import streamlit as st

st.title("Trends")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

st.info("Not built yet (Rol 4). See AGENTS.md: core.data.load_measurements() and get_baseline().")
