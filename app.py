# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Entry point (`streamlit run app.py`): page config and navigation. Owner: Ansel.

Screens and navigation follow docs/ASTRONAUT_HEALTH_APP_SPEC.md (AGENTS.md 3 and 16): no sidebar
menu, people move with buttons and cards. This file lists the screens and adds the top-left
back button: Main Menu goes back to Welcome; every other screen goes back to Main Menu.
On Welcome it hides Streamlit's header so the conversation fills the viewport.
A new page must be added to PAGES. Look: docs/UI_STYLE.md (theme in .streamlit/config.toml, the
shared styles and the mission status bar in core/ui.py).
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

st.set_page_config(page_title="Astronaut Health Monitor", page_icon=":material/monitor_heart:", layout="wide")

from core import ui  # noqa: E402  (after the core purge above)

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
ui.styles()

if navigation.url_path != welcome.url_path and not (
        st.session_state.get("astronaut") and st.session_state.get("environment")):
    # Every screen needs both choices: without them (refresh on a deep link, new tab) go to the
    # Welcome, the same on every screen (docs/CODE_REVIEW.md UX-6).
    st.switch_page(welcome)

if navigation.url_path == welcome.url_path:
    # Full-viewport Welcome (docs/FRONTEND_MASCOT_LAYOUT.md 2), conversation centred.
    st.html("""<style>
      .st-key-welcome_screen { min-height: calc(100vh - 2.5rem); display: flex; flex-direction: column;
                               justify-content: center; max-width: 56rem; margin: 0 auto; }
    </style>""")
else:
    st.session_state.pop("welcome_step", None)   # arriving at Welcome always starts at step 1
    # Top row: back (Main Menu goes back to Welcome, every other screen to Main Menu) and the
    # mission status bar. No page titles (docs/UI_STYLE.md).
    back_col, status_col = st.columns([1, 6], vertical_alignment="center")
    on_menu = navigation.url_path == menu.url_path
    if back_col.button("Change astronaut" if on_menu else "Main Menu", icon=":material/arrow_back:",
                       type="tertiary", key="app_back"):
        st.switch_page(welcome if on_menu else menu)
    with status_col:
        ui.status_bar(st.session_state["astronaut"], st.session_state["environment"])
navigation.run()
