# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Protocol: run the active episode step by step. Owner: Rol 6."""
import streamlit as st

st.title("Protocol")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

st.info("Not built yet (Rol 6). See AGENTS.md: core.protocol_engine.current_step() and submit().")
