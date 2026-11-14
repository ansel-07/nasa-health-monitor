# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

Screens and navigation follow docs/ASTRONAUT_HEALTH_APP_SPEC.md (AGENTS.md 3 and 16): no sidebar
menu, people move with buttons and cards. This file lists the screens and adds the top-left
back button: Main Menu goes back to Welcome; every other screen goes back to Main Menu.
A new page must be added to PAGES.
"""
import streamlit as st

st.set_page_config(page_title="Astronaut Health Monitor", page_icon="🩺", layout="wide")

welcome = st.Page("pages/0_Home.py", title="Welcome", default=True)
menu = st.Page("pages/5_Menu.py", title="Main Menu")
PAGES = [
    welcome,
    menu,
    st.Page("pages/1_Check_in.py", title="Check-in"),
    st.Page("pages/2_Protocol.py", title="Protocols"),
    st.Page("pages/3_Trends.py", title="Trends"),
    st.Page("pages/4_Tutorials.py", title="Tutorials"),
]
navigation = st.navigation(PAGES, position="hidden")

if navigation.url_path == menu.url_path:
    if st.button("← Back"):
        st.switch_page(welcome)
elif navigation.url_path != welcome.url_path:
    if st.button("← Main Menu"):
        st.switch_page(menu)
navigation.run()
