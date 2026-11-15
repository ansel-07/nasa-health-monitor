# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Main Menu: Check-in, Trends and Tutorials cards, plus the demo controls. Owner: Ansel.

docs/ASTRONAUT_HEALTH_APP_SPEC.md, screen 2, with the layout of docs/FRONTEND_MASCOT_LAYOUT.md 3:
compact mascot line (docs/UI_STYLE.md), urgent alarms, then one row of cards below. Protocols is not a menu item: its card appears only while the astronaut
has an active episode or pending alerts. The top-left back button (to Welcome) comes from app.py.
"""
from datetime import datetime

import streamlit as st

from core import activity, config, data, episodes, mascot, mission, ui

if "astronaut" not in st.session_state or "environment" not in st.session_state:
    st.switch_page("pages/0_Home.py")

astronaut = st.session_state["astronaut"]
environment = st.session_state["environment"]
names = dict(zip(*[data.load_astronauts()[c] for c in ("id", "name")]))
open_episode = data.get_open_episode(astronaut)
pending = episodes.get_pending(astronaut)

mascot.voice_toggle()

# Urgent subjective symptoms (docs/sintomas_subjetivos_atrofia_SANS.md section 3) prevail and stay
# visible until the astronaut marks them resolved in Check-in; they never close by themselves.
definitions = config.load_subjective_issues().get("issues", {})
try:
    alarms = [definitions[item["issue"]] for item in activity.active_issues(astronaut)
              if definitions.get(item["issue"], {}).get("alarm")]
except (ValueError, KeyError, OSError):
    alarms = []

# Placeholder lines: final wording and moods are still to be decided by the team.
if alarms:
    text, mood = "You reported an urgent symptom. Stop the risky task and contact the crew medical officer now.", "serious"
elif open_episode and open_episode["status"] == "active":
    text, mood = f"{names[astronaut]}, you have a protocol to follow.", "worried"
elif open_episode:
    text, mood = f"{names[astronaut]}, an alert needs a repeat measurement in Check-in.", "worried"
elif pending:
    text, mood = f"{names[astronaut]}, {len(pending)} alert(s) are waiting for you.", "thinking"
else:
    text, mood = f"Hi {names[astronaut]}! What would you like to do?", "happy"

mascot.say(text, mood, size="medium")

for alarm in alarms:
    st.error(f"Urgent symptom: {alarm['label']}. {alarm['action']} "
             "When it is no longer present, mark it as resolved in Check-in → Subjective issues.")

# Cards with their status (docs/UI_STYLE.md): what is due or waiting, never a health verdict.
checkins = config.load_checkins()
levels = [activity.bar_level(astronaut, "check_in", checkin_id) for checkin_id in checkins]
problems = config.load_problems()
ready = sum(activity.can_repeat_tutorial(astronaut, problem_id) for problem_id in problems)
tracked = len(data.latest_values(astronaut))
repeat_waiting = bool(open_episode and open_episode["status"] == "pending_confirmation")
checkin_status = ("Repeat measurement waiting" if repeat_waiting
                  else f"Lowest recency {min(levels)}%" if levels else "")
CARDS = [("Check-in", "pages/1_Check_in.py", "monitor_heart", checkin_status, min(levels) if levels else None),
         ("Trends", "pages/3_Trends.py", "show_chart", f"{tracked} indicators tracked", None),
         ("Tutorials", "pages/4_Tutorials.py", "school", f"{ready} of {len(problems)} ready to practise", None)]
if (open_episode and open_episode["status"] == "active") or pending:
    status = (f"In progress: {problems.get(open_episode['problem'], {}).get('name', 'protocol')}"
              if open_episode and open_episode["status"] == "active" else f"{len(pending)} alert(s) waiting")
    CARDS.insert(0, ("Protocols", "pages/2_Protocol.py", "medical_services", status, None))
for column, (label, page, icon, status, level) in zip(st.columns(len(CARDS)), CARDS):
    with column:
        if ui.card(f"menu_{label}", label, icon, status, level, primary=label == "Protocols" or (label == "Check-in" and repeat_waiting)):
            st.switch_page(page)

if feedback := st.session_state.pop("menu_feedback", None):
    level, text = feedback
    (st.error if level == "error" else st.info)(text)

# Demo controls: a discreet panel in the bottom-left corner, not part of the product.
with st.container(key="demo_panel"):
    st.html("<style>.st-key-demo_panel { position: fixed; bottom: 1rem; left: 1.25rem; z-index: 1000; "
            "width: auto !important; }</style>")
    with st.popover("Demo controls", icon=":material/science:"):
        now = mission.now()
        day = (now - datetime.fromisoformat(config.load_mission()["start"])).days + 1
        st.caption(f"Mission time: {now:%Y-%m-%d %H:%M} (day {day}) · {config.load_environments()[environment]['name']}")
        if st.button("Advance mission 24 h", icon=":material/fast_forward:", use_container_width=True):
            try:
                with st.spinner("Advancing mission time and checking the new measurements…"):
                    result = mission.advance_and_detect(24, environment)
            except (ValueError, KeyError, OSError) as error:
                # The clock may have moved; rows not processed are kept and retried on the next
                # advance (AGENTS.md 5.5, #77). Show it instead of a Python error page.
                st.session_state["menu_feedback"] = ("error", "Mission time could not be fully advanced: "
                                                     f"{error} Unprocessed measurements are kept and will be "
                                                     "checked on the next advance.")
            else:
                text = f"Mission time advanced 24 h: {result['revealed']} new simulated measurement(s)"
                if result.get("recovered"):
                    text += f", {result['recovered']} left from an earlier advance"
                text += (f"; new alert for {', '.join(names[a] for a in result['new_alerts'])}."
                         if result["new_alerts"] else ".")
                st.session_state["menu_feedback"] = ("info", text)
            st.rerun()
        if st.button("Reset demo", icon=":material/restart_alt:", use_container_width=True):
            try:
                data.reset_demo()
            except OSError as error:
                st.session_state["menu_feedback"] = ("error", f"Demo data could not be reset: {error}")
            else:
                # Check-in keeps drafts, retries and feedback in the session (#132): drop them with
                # the data. Astronaut, environment, voice and other screens' state are kept.
                for key in [k for k in st.session_state if str(k).startswith("check_in_")]:
                    del st.session_state[key]
                st.session_state["menu_feedback"] = ("info", "Demo data reset.")
            st.rerun()
