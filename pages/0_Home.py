# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Welcome: a short conversation with the mascot, then Main Menu. Owner: Ansel.

docs/FRONTEND_MASCOT_LAYOUT.md section 2 (overrides spec screen 1): full viewport, big centred
mascot, conversational buttons, no dropdowns and no NEXT. Two steps in
st.session_state["welcome_step"]: 1 = who are you (astronaut buttons), 2 = where is the mission
(environment buttons). app.py resets the step whenever another screen is shown, so arriving here
always starts at step 1. Run through app.py (st.navigation), which sets the page config.
"""
import streamlit as st

from core import config, data, mascot

astronauts = data.load_astronauts()
environments = config.load_environments()
names = dict(zip(astronauts["id"], astronauts["name"]))

step = st.session_state.get("welcome_step", 1)
if step == 2 and st.session_state.get("astronaut") not in names:
    step = 1

with st.container(key="welcome_screen"):
    mascot.voice_toggle()
    st.title("SpaceDoc")
    st.caption("Your health, guided through every mission. Prototype: it guides; it does not diagnose.")
    if step == 1:
        mascot.say("Hello! Who are you?", "happy", size="large")
        for column, astronaut_id in zip(st.columns(len(names) or 1), names):
            if column.button(names[astronaut_id], key=f"welcome_astronaut_{astronaut_id}",
                             use_container_width=True):
                st.session_state["astronaut"] = astronaut_id
                st.session_state["welcome_step"] = 2
                st.rerun()
    else:
        mascot.say(f"Hi {names[st.session_state['astronaut']]}! Where is the mission?", "happy", size="large")
        for column, env_id in zip(st.columns(len(environments) or 1), environments):
            if column.button(environments[env_id]["name"], key=f"welcome_environment_{env_id}",
                             use_container_width=True):
                st.session_state["environment"] = env_id
                st.session_state.pop("welcome_step", None)
                st.switch_page("pages/5_Menu.py")
        if st.button("← Change astronaut", key="welcome_back"):
            st.session_state["welcome_step"] = 1
            st.rerun()

    # Approved copy (Gonzalo, #39), with the steps following the current screens.
    with st.expander("Try it in 1 minute"):
        st.markdown("1. " + 'Choose **Astronaut A**, then **International Space Station**. In Main Menu → *Demo controls*, press **Reset demo**. You will explore fictional, synthetic measurements.')
        st.markdown("2. " + 'Press **Advance mission 24 h** to reveal an ocular measurement alert. Open **Check-in** to compare it with your personal pre-flight baseline.')
        st.markdown("3. " + 'Use **Simulate wait** and repeat the flagged measurement with the demo value (**360** µm) to confirm the anomaly.')
        st.markdown("4. " + 'Open **Protocols** and follow the guidance through to medical follow-up. SpaceDoc guides you; it does not diagnose.')
