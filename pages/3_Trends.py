# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: Trends implementation generated with Claude Code and reviewed by Fran.
"""Trends: history charts with colour bands and personal baseline. Owner: Fran.

No mascot on this screen (AGENTS.md, section 8). Charts come from core.charts;
data only through core.data and core.config (pages never read files).
"""
import streamlit as st

from core import charts, config, data

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
