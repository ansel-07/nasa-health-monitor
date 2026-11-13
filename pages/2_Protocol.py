# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Protocol: run the active episode step by step. Owner: Javi.

Mascot: says the text of each step (AGENTS.md, section 8).
"""
import streamlit as st

from core import mascot

st.title("Protocol")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

mascot.say("The protocol screen is not built yet.", "neutral")
st.info("Not built yet (Javi). See AGENTS.md: core.protocol_engine.current_step() and submit().")
