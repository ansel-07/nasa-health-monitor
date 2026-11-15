# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

Screens and navigation follow docs/ASTRONAUT_HEALTH_APP_SPEC.md (AGENTS.md 3 and 16): no sidebar
menu, people move with buttons and cards. This file lists the screens and adds the top-left
back button: Main Menu goes back to Welcome; every other screen goes back to Main Menu.
On Welcome it hides Streamlit's header so the conversation fills the viewport.
A new page must be added to PAGES.
"""
import sys
from pathlib import Path

import streamlit as st

# After a redeploy, Streamlit re-reads app.py and the pages but can keep the core.* modules it
# had imported, so a page could call a function that its old core module does not have (#174).
# When any core/*.py file changed since the last run (or no run has recorded it yet), drop every
# cached core module: the pages' `from core import ...` then loads the new code. Process-wide
# stamp, compared on every run; on a fresh process nothing is cached, so the first drop is free.
_CORE_STAMP = tuple(sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size)
                           for p in (Path(__file__).parent / "core").glob("*.py")))
# Not under pytest: tests patch the imported core modules, and AppTest runs this file in their process.
if "pytest" not in sys.modules and getattr(sys, "_spacedoc_core_stamp", None) != _CORE_STAMP:
    for _name in [name for name in sys.modules if name == "core" or name.startswith("core.")]:
        del sys.modules[_name]
sys._spacedoc_core_stamp = _CORE_STAMP

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
