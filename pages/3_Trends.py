# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Trends: history charts with colour bands and personal baseline. Owner: Fran.

No mascot on this screen (AGENTS.md, section 8). Charts come from core.charts.
"""
import streamlit as st

st.title("Trends")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

st.info("Not built yet (Fran). See AGENTS.md: core.charts.indicator_chart().")
