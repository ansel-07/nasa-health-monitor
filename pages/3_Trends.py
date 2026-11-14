# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Trends implementation generated with Claude Code and reviewed by Fran.
"""Trends: history charts with colour bands and personal baseline. Owner: Fran.

No mascot on this screen (AGENTS.md, section 8). Charts come from core.charts;
data only through core.data and core.config (pages never read files).
"""
from datetime import datetime

import streamlit as st

from core import charts, config, data, mission

ADVANCE_HOURS = 24
FEEDBACK_KEY = "trends_advance_feedback"

st.title("Trends")

if "astronaut" not in st.session_state:
    st.warning("Choose an astronaut on the Home page first.")
    st.stop()

astronaut = st.session_state["astronaut"]
environment = st.session_state.get("environment")

astronauts = data.load_astronauts()
names = dict(zip(astronauts["id"], astronauts["name"]))
env_name = config.load_environments().get(environment, {}).get("name", environment)
st.caption(f"{names.get(astronaut, astronaut)} · {env_name}")


def _advance_mission() -> dict:
    """Advance the clock and send every newly visible measurement to episode detection.

    Returns the feedback to show after the rerun: {"level", "text", "alert"}.
    """
    try:
        result = mission.advance_and_detect(ADVANCE_HOURS, environment)
    except (ValueError, KeyError, OSError) as error:
        return {"level": "error", "alert": False,
                "text": f"Mission time advanced, but detection failed: {error}"}
    opened = result["new_alerts"]
    text = f"Mission time advanced {ADVANCE_HOURS} h: {result['revealed']} new simulated measurement(s)."
    if not opened:
        return {"level": "info", "text": text, "alert": False}
    who = ", ".join(names.get(a, a) for a in opened)
    return {"level": "warning", "text": f"{text} New alert for: {who}.", "alert": astronaut in opened}


with st.container(border=True):
    st.markdown("**Demo controls**")
    st.caption("Simulates the passing of mission time for the demo: each click reveals the "
               "next day of simulated measurements, which may open alerts.")
    now = mission.now()
    day = (now - datetime.fromisoformat(config.load_mission()["start"])).days + 1
    col_time, col_button = st.columns([3, 1])
    col_time.write(f"Mission time: **{now:%Y-%m-%d %H:%M}** (day {day})")
    if col_button.button(f"Advance {ADVANCE_HOURS} h"):
        st.session_state[FEEDBACK_KEY] = _advance_mission()
        st.rerun()
    # Kept (not popped) so the "Go to Check-in" button still exists on the rerun its click causes.
    feedback = st.session_state.get(FEEDBACK_KEY)
    if feedback:
        getattr(st, feedback["level"])(feedback["text"])
        if feedback["alert"] and st.button("Go to Check-in"):
            st.switch_page("pages/1_Check_in.py")

# Test fixtures (ids starting with "_") are never shown as health content.
indicators = {key: info for key, info in config.load_indicators().items() if not key.startswith("_")}
if not indicators:
    st.info("No indicators configured yet.")
    st.stop()


def _label(key: str) -> str:
    name = indicators[key].get("name", "")
    return key if not name or name.startswith("TODO") else name


indicator = st.selectbox("Indicator", list(indicators), format_func=_label,
                         key=f"trends_indicator:{astronaut}")
unit = indicators[indicator].get("unit", "")

st.plotly_chart(charts.indicator_chart(astronaut, indicator, environment=environment))

latest = data.latest_values(astronaut).get(indicator)
baseline = data.get_baseline(astronaut, indicator)
z = data.z_score(astronaut, indicator, latest) if latest is not None else None

col_latest, col_baseline, col_z = st.columns(3)
col_latest.metric("Latest value", "—" if latest is None else f"{latest:.1f} {unit}")
col_baseline.metric(
    "Personal baseline (pre-flight)",
    "—" if baseline is None else f"{baseline['mean']:.1f} ± {baseline['std']:.1f} {unit}",
    help=None if baseline is None else f"Mean ± standard deviation of {baseline['n']} pre-flight measurements.",
)
col_z.metric("Distance from baseline (z)", "—" if z is None else f"{z:+.1f}",
             help="How many standard deviations the latest value is from the personal baseline.")

if baseline is None:
    st.caption("No pre-flight measurements for this indicator, so there is no personal baseline yet.")
