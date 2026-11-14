# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

The screens live in pages/ (pages/0_Home.py is the Home). There is no sidebar menu: people
move with the buttons of each screen (provisional, until the team's UI document). Every
screen except the Home gets a "Back to Home" button from here.
"""
import streamlit as st

st.set_page_config(page_title="Astronaut Health Monitor", page_icon="🩺", layout="wide")

home = st.Page("pages/0_Home.py", title="Home", default=True)
navigation = st.navigation([
    home,
    st.Page("pages/1_Check_in.py", title="Check-in"),
    st.Page("pages/2_Protocol.py", title="Protocol"),
    st.Page("pages/3_Trends.py", title="Trends"),
], position="hidden")

if navigation.url_path != home.url_path and st.button("← Back to Home"):
    st.switch_page(home)
navigation.run()
