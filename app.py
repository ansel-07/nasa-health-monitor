# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

The screens live in pages/ (pages/0_Home.py is the Home). This file only names them in the sidebar, so the
first one is "Home" instead of the file name. Things that must appear on every screen go here.
"""
import streamlit as st

st.set_page_config(page_title="Astronaut Health Monitor", page_icon="🩺", layout="wide")

navigation = st.navigation([
    st.Page("pages/0_Home.py", title="Home", default=True),
    st.Page("pages/1_Check_in.py", title="Check-in"),
    st.Page("pages/2_Protocol.py", title="Protocol"),
    st.Page("pages/3_Trends.py", title="Trends"),
])
navigation.run()
