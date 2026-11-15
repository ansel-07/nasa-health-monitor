# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

Screens and navigation follow docs/ASTRONAUT_HEALTH_APP_SPEC.md (AGENTS.md 3 and 16): no sidebar
menu, people move with buttons and cards. This file lists the screens and adds the top-left
back button: Main Menu goes back to Welcome; every other screen goes back to Main Menu.
On Welcome it hides Streamlit's header so the conversation fills the viewport.
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
# Primary buttons are cyan (theme primaryColor): dark text keeps them readable on a projector.
st.html("<style>[data-testid='stBaseButton-primary'], [data-testid='stBaseButton-primaryFormSubmit'] "
        "{ color: #111111 !important; } [data-testid='stBaseButton-primary'] p, "
        "[data-testid='stBaseButton-primaryFormSubmit'] p { color: #111111 !important; }</style>")

if navigation.url_path != welcome.url_path and not (
        st.session_state.get("astronaut") and st.session_state.get("environment")):
    # Every screen needs both choices: without them (refresh on a deep link, new tab) go to the
    # Welcome, the same on every screen (docs/CODE_REVIEW.md UX-6).
    st.switch_page(welcome)

if navigation.url_path == welcome.url_path:
    # Full-viewport Welcome (docs/FRONTEND_MASCOT_LAYOUT.md 2): no Streamlit header or top padding.
    st.html("""<style>
      [data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
      [data-testid="stMainBlockContainer"], .block-container { padding-top: 1rem; padding-bottom: 1rem; }
      .st-key-welcome_screen { min-height: calc(100vh - 2rem); display: flex; flex-direction: column;
                               justify-content: center; max-width: 56rem; margin: 0 auto; }
    </style>""")
else:
    st.session_state.pop("welcome_step", None)   # arriving at Welcome always starts at step 1

if navigation.url_path == menu.url_path:
    if st.button("← Back"):
        st.switch_page(welcome)
elif navigation.url_path != welcome.url_path:
    if st.button("← Main Menu"):
        st.switch_page(menu)
navigation.run()
