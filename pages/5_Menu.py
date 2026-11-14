# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Main Menu: Check-in, Trends and Tutorials cards, plus the demo controls. Owner: Ansel.

docs/ASTRONAUT_HEALTH_APP_SPEC.md, screen 2, with the mascot of AGENTS.md 16 (small on the left,
cards on the right). Protocols is not a menu item: its card appears only while the astronaut
has an active episode or pending alerts. The top-left back button (to Welcome) comes from app.py.
"""
import streamlit as st

from core import config, data, episodes, mascot, mission

if "astronaut" not in st.session_state or "environment" not in st.session_state:
    st.switch_page("pages/0_Home.py")

astronaut = st.session_state["astronaut"]
environment = st.session_state["environment"]
names = dict(zip(*[data.load_astronauts()[c] for c in ("id", "name")]))
open_episode = data.get_open_episode(astronaut)
pending = episodes.get_pending(astronaut)

_, voice_col = st.columns([5, 1])
with voice_col:
    mascot.voice_toggle()

# Placeholder lines: final wording and moods are still to be decided by the team.
if open_episode and open_episode["status"] == "active":
    text, mood = f"{names[astronaut]}, you have a protocol to follow.", "worried"
elif open_episode:
    text, mood = f"{names[astronaut]}, an alert needs a repeat measurement in Check-in.", "worried"
elif pending:
    text, mood = f"{names[astronaut]}, {len(pending)} alert(s) are waiting for you.", "thinking"
else:
    text, mood = f"Hi {names[astronaut]}! What would you like to do?", "happy"

CARDS = [("Check-in", "pages/1_Check_in.py"), ("Trends", "pages/3_Trends.py"),
         ("Tutorials", "pages/4_Tutorials.py")]
with mascot.beside(text, mood):
    if (open_episode and open_episode["status"] == "active") or pending:
        if st.button("Protocols", type="primary", use_container_width=True):
            st.switch_page("pages/2_Protocol.py")
    for label, page in CARDS:
        if st.button(label, use_container_width=True):
            st.switch_page(page)

st.divider()
with st.expander("Demo controls"):
    now = mission.now()
    day = (now - __import__("datetime").datetime.fromisoformat(config.load_mission()["start"])).days + 1
    st.caption(f"Mission time: {now:%Y-%m-%d %H:%M} (day {day}) · {config.load_environments()[environment]['name']}")
    advance_col, reset_col = st.columns(2)
    if advance_col.button("Advance mission 24 h", use_container_width=True):
        result = mission.advance_and_detect(24, environment)
        st.session_state["menu_feedback"] = (
            f"Mission time advanced 24 h: {result['revealed']} new simulated measurement(s)"
            + (f"; new alert for {', '.join(names[a] for a in result['new_alerts'])}." if result["new_alerts"] else "."))
        st.rerun()
    if reset_col.button("Reset demo", use_container_width=True):
        data.reset_demo()
        st.session_state["menu_feedback"] = "Demo data reset."
        st.rerun()
    if feedback := st.session_state.pop("menu_feedback", None):
        st.info(feedback)
