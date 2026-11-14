# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Welcome: choose who you are and where the mission is, then NEXT. Owner: Ansel.

docs/ASTRONAUT_HEALTH_APP_SPEC.md, screen 1, with the mascot of AGENTS.md 16: large and centered,
two selectors below (no default choice), NEXT bottom-right, enabled only when both are chosen.
Run through app.py (st.navigation), which sets the page config.
"""
import streamlit as st

from core import config, data, mascot

astronauts = data.load_astronauts()
environments = config.load_environments()

ids = list(astronauts["id"])
names = dict(zip(astronauts["id"], astronauts["name"]))
env_ids = list(environments)


def _index(options: list, key: str):
    """Keep a choice made earlier in this session (coming back from Main Menu); else no default."""
    value = st.session_state.get(key)
    return options.index(value) if value in options else None


_, voice_col = st.columns([5, 1])
with voice_col:
    mascot.voice_toggle()

_, center, _ = st.columns([1, 2, 1])
with center:
    st.title("SpaceDoc")
    st.caption("Your health, guided through every mission. Prototype: it guides; it does not diagnose.")
    mascot.say("Hello! Tell me who you are and where the mission is.", "happy", size="large")
    pick_astronaut, pick_environment = st.columns(2)
    with pick_astronaut:
        astronaut = st.selectbox("Who are you?", ids, index=_index(ids, "astronaut"),
                                 format_func=lambda i: names[i], placeholder="Select astronaut")
    with pick_environment:
        environment = st.selectbox("Where is the mission?", env_ids, index=_index(env_ids, "environment"),
                                   format_func=lambda e: environments[e]["name"], placeholder="Select mission")
    _, next_col = st.columns([3, 1])
    with next_col:
        ready = astronaut is not None and environment is not None
        if st.button("NEXT", type="primary", disabled=not ready, use_container_width=True):
            st.session_state["astronaut"] = astronaut
            st.session_state["environment"] = environment
            st.switch_page("pages/5_Menu.py")

    # Approved copy (Gonzalo, #39), with the steps following the current screens.
    with st.expander("Try it in 1 minute"):
        st.markdown("1. " + 'Choose **Astronaut A** and **International Space Station**, then **NEXT**. In Main Menu → *Demo controls*, press **Reset demo**. You will explore fictional, synthetic measurements.')
        st.markdown("2. " + 'Press **Advance mission 24 h** to reveal an ocular measurement alert. Open **Check-in** to compare it with your personal pre-flight baseline.')
        st.markdown("3. " + 'Use **Simulate wait** and repeat the flagged measurement with the demo value to confirm the anomaly.')
        st.markdown("4. " + 'Open **Protocols** and follow the guidance through to medical follow-up. SpaceDoc guides you; it does not diagnose.')
