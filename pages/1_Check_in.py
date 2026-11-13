# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Check-in: measurement form, trigger alert and confirmation step. Owner: Juan Carlos.

Mascot: large at the top; small in a column next to the chart when a chart is shown
(AGENTS.md, section 8). Chart: core.charts.indicator_chart(..., compact=True).
"""
import streamlit as st

from core import mascot

st.title("Check-in")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

mascot.say("Check-in is not built yet.", "neutral")
st.info("Not built yet (Juan Carlos). See AGENTS.md: core.episodes.on_new_measurement() and confirm().")
